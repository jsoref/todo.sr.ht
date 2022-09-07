package imports

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
	"time"

	"git.sr.ht/~sircmpwn/core-go/database"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/loaders"
)

type TrackerDump struct {
	Owner   Owner    `json:"owner"`
	Name    string   `json:"name"`
	Labels  []Label  `json:"labels"`
	Tickets []Ticket `json:"tickets"`
}

type Owner struct {
	CanonicalName string `json:"canonical_name"`
	Name          string `json:"name"`
	Email         string `json:"email"`
	URL           string `json:"url"`
	Location      string `json:"location"`
	Bio           string `json:"bio"`
}

type Label struct {
	Name   string `json:"name"`
	Colors struct {
		Background string `json:"background"`
		Foreground string `json:"text"`
	} `json:"colors"`
	Created time.Time `json:"created"`
	Tracker Tracker   `json:"tracker"`
}

type Tracker struct {
	ID      int       `json:"id"`
	Owner   User      `json:"owner"`
	Created time.Time `json:"created"`
	Updated time.Time `json:"updated"`
	Name    string    `json:"name"`
}

type Ticket struct {
	ID         int          `json:"id"`
	Ref        string       `json:"ref"`
	Tracker    Tracker      `json:"tracker"`
	Subject    string       `json:"title"`
	Created    time.Time    `json:"created"`
	Updated    time.Time    `json:"updated"`
	Submitter  *Participant `json:"submitter"` // null in shorter ticket dicts
	Body       string       `json:"description"`
	Status     string       `json:"status"`
	Resolution string       `json:"resolution"`
	Labels     []string     `json:"labels"`
	Assignees  []User       `json:"assignees"`
	Upstream   string       `json:"upstream"`
	Signature  string       `json:"X-Payload-Signature"`
	Nonce      string       `json:"X-Payload-Nonce"`
	Events     []Event      `json:"events"`
}

type Event struct {
	ID            int          `json:"id"`
	Created       time.Time    `json:"created"`
	EventType     []string     `json:"event_type"`
	OldStatus     *string      `json:"old_status"`
	OldResolution *string      `json:"old_resolution"`
	NewStatus     *string      `json:"new_status"`
	NewResolution *string      `json:"new_resolution"`
	User          *Participant `json:"user"`
	Ticket        *Ticket      `json:"ticket"`
	Comment       *Comment     `json:"comment"`
	Label         *string      `json:"label"`
	ByUser        *Participant `json:"by_user"`
	FromTicket    *Ticket      `json:"from_ticket"`
	Upstream      string       `json:"upstream"`
	Signature     string       `json:"X-Payload-Signature"`
	Nonce         string       `json:"X-Payload-Nonce"`
}

type Participant struct {
	Type          string `json:"type"`
	CanonicalName string `json:"canonical_name"`
	Name          string `json:"name"`
	Address       string `json:"address"`
	ExternalID    string `json:"external_id"`
	ExternalURL   string `json:"external_url"`
}

type User struct {
	CanonicalName string `json:"canonical_name"`
	Name          string `json:"name"`
}

type Comment struct {
	ID        int         `json:"id"`
	Created   time.Time   `json:"created"`
	Submitter Participant `json:"submitter"`
	Text      string      `json:"text"`
}

func importParticipant(ctx context.Context, part Participant, upstream, ourUpstream string) (int, error) {
	switch part.Type {
	case "user":
		if upstream == ourUpstream {
			part, err := loaders.ForContext(ctx).ParticipantsByUsername.Load(part.Name)
			if err == nil {
				return part.ID, nil
			}
		}
		return importExternalParticipant(ctx, part.CanonicalName,
			upstream+"/"+part.CanonicalName)
	case "email":
		// TODO: check if the email is registered on this upstream?
		return importEmailParticipant(ctx, part.Address, part.Name)
	case "external":
		// TODO: check if the user is registered on this upstream?
		return importExternalParticipant(ctx, part.ExternalID, part.ExternalURL)
	default:
		return 0, fmt.Errorf("invalid participant type %q", part.Type)
	}
}

func importEmailParticipant(ctx context.Context, address, name string) (int, error) {
	var partID int
	err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			INSERT INTO participant (
				created, participant_type, email, email_name
			) VALUES (
				NOW() at time zone 'utc',
				'email',
				$1, $2
			)
			ON CONFLICT ON CONSTRAINT participant_email_key
			DO UPDATE SET created = participant.created
			RETURNING id
		`, address, name)
		if err := row.Scan(&partID); err != nil {
			return err
		}
		return nil
	})
	if err != nil {
		return 0, err
	}
	return partID, nil
}

func importExternalParticipant(ctx context.Context, id, url string) (int, error) {
	var partID int
	err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			INSERT INTO participant (
				created, participant_type, external_id, external_url
			) VALUES (
				NOW() at time zone 'utc',
				'external',
				$1, $2
			)
			ON CONFLICT ON CONSTRAINT participant_external_id_key
			DO UPDATE SET created = participant.created
			RETURNING id
		`, id, url)
		if err := row.Scan(&partID); err != nil {
			return err
		}
		return nil
	})
	if err != nil {
		return 0, err
	}
	return partID, nil
}

func importTrackerDump(ctx context.Context, trackerID int, dump io.Reader, ourUpstream string) error {
	b, err := io.ReadAll(dump)
	if err != nil {
		return err
	}
	var tracker TrackerDump
	if err := json.Unmarshal(b, &tracker); err != nil {
		return err
	}

	// Create labels
	labelIDs := map[string]int{}
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		for _, label := range tracker.Labels {
			row := tx.QueryRowContext(ctx, `
				INSERT INTO label (
					created, updated, tracker_id, name, color, text_color
				) VALUES (
					$1, $1, $2, $3, $4, $5
				) RETURNING id
			`, label.Created, trackerID, label.Name, label.Colors.Background, label.Colors.Foreground)
			var labelID int
			if err := row.Scan(&labelID); err != nil {
				return err
			}
			labelIDs[label.Name] = labelID
		}
		return nil
	}); err != nil {
		return err
	}

	defer func() {
		if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
			_, err := tx.ExecContext(ctx, `
				UPDATE tracker
				SET import_in_progress = false
				WHERE id = $1
			`, trackerID)
			return err
		}); err != nil {
			panic(err)
		}
	}()

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		var nextTicketID int
		row := tx.QueryRowContext(ctx,
			`SELECT next_ticket_id FROM tracker WHERE id = $1`,
			trackerID)
		if err := row.Scan(&nextTicketID); err != nil {
			return err
		}
		// Make sure that the tracker does not have any existing tickets
		// to avoid conflicts.
		if nextTicketID != 1 {
			return errors.New("Tracker must not have any existing tickets")
		}

		var maxTicketID int

		for _, ticket := range tracker.Tickets {
			submitterID, err := importParticipant(ctx, *ticket.Submitter, ticket.Upstream, ourUpstream)
			if err != nil {
				return err
			}

			// Compute the max ticket ID. We can't use the number of tickets as
			// the next ticket ID because that won't include deleted tickets
			if ticket.ID > maxTicketID {
				maxTicketID = ticket.ID
			}
			// We don't need to check for existing tickets since we ensured that
			// the tracker has no tickets.
			row := tx.QueryRowContext(ctx, `
				INSERT INTO ticket (
					created, updated,
					tracker_id, scoped_id,
					submitter_id, title, description,
					status, resolution, authenticity
				) VALUES (
					$1, $2, $3, $4, $5, $6, $7, $8, $9, $10
				)
				RETURNING id
			`, ticket.Created, ticket.Updated, trackerID, ticket.ID,
				submitterID, ticket.Subject, ticket.Body,
				model.TicketStatus(strings.ToUpper(ticket.Status)).ToInt(),
				model.TicketResolution(strings.ToUpper(ticket.Resolution)).ToInt(),
				model.AUTH_UNAUTHENTICATED)
			var ticketPKID int
			if err := row.Scan(&ticketPKID); err != nil {
				return err
			}

			for _, label := range ticket.Labels {
				_, err := tx.ExecContext(ctx, `
					INSERT INTO ticket_label (
						created, ticket_id, label_id, user_id
					) VALUES (
						NOW() at time zone 'utc',
						$1, $2,
						(SELECT owner_id FROM tracker WHERE id = $3)
					)
				`, ticketPKID, labelIDs[label], trackerID)
				if err != nil {
					return err
				}
			}

			// TODO: assignees

			for _, event := range ticket.Events {
				var (
					commentID       *int
					labelID         *int
					partID          *int
					oldStatus       *int
					newStatus       *int
					oldResolution   *int
					newResolution   *int
					byParticipantID *int
				)

				var eventType int
				for _, etype := range event.EventType {
					eventType |= eventTypeMap[etype]
				}
				if eventType == 0 {
					return fmt.Errorf("failed to import ticket #%d: invalid ticket event", ticket.ID, eventType)
				}

				if event.User != nil {
					userPartID, err := importParticipant(ctx, *event.User, event.Upstream, ourUpstream)
					if err != nil {
						return err
					}
					partID = &userPartID
				}

				if eventType&model.EVENT_COMMENT != 0 {
					submitterID, err := importParticipant(ctx, event.Comment.Submitter, event.Upstream, ourUpstream)
					if err != nil {
						return err
					}

					row := tx.QueryRowContext(ctx, `
						INSERT INTO ticket_comment (
							created, updated, submitter_id, ticket_id, text,
							authenticity
						) VALUES (
							$1, $1, $2, $3, $4, $5
						) RETURNING id
					`, event.Comment.Created, submitterID, ticketPKID, event.Comment.Text,
						model.AUTH_UNAUTHENTICATED)
					var _commentID int
					if err := row.Scan(&_commentID); err != nil {
						return err
					}
					commentID = &_commentID

					_, err = tx.ExecContext(ctx, `
						UPDATE ticket
						SET comment_count = comment_count + 1
						WHERE id = $1
					`, ticketPKID)
					if err != nil {
						return err
					}
				}
				if eventType&model.EVENT_STATUS_CHANGE != 0 {
					oldStatus = convertStatusToInt(event.OldStatus)
					newStatus = convertStatusToInt(event.NewStatus)
					oldResolution = convertResolutionToInt(event.OldResolution)
					newResolution = convertResolutionToInt(event.NewResolution)
				}
				if eventType&model.EVENT_LABEL_ADDED != 0 ||
					eventType&model.EVENT_LABEL_REMOVED != 0 {
					_labelID := labelIDs[*event.Label]
					labelID = &_labelID
				}
				if eventType&model.EVENT_ASSIGNED_USER != 0 ||
					eventType&model.EVENT_UNASSIGNED_USER != 0 {
					partID, err := importParticipant(ctx, *event.ByUser, event.Upstream, ourUpstream)
					if err != nil {
						return err
					}
					byParticipantID = &partID
				}
				if eventType&model.EVENT_USER_MENTIONED != 0 {
					// Magic event type, do not import
					continue
				}
				if eventType&model.EVENT_TICKET_MENTIONED != 0 {
					// TODO: Could reference tickets imported in later iterations
					continue
				}

				_, err := tx.ExecContext(ctx, `
					INSERT INTO event (
						created, event_type, participant_id, ticket_id,
						old_status, new_status, old_resolution, new_resolution,
						comment_id, label_id, by_participant_id
					) VALUES (
						$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
					)
				`, event.Created, eventType, partID, ticketPKID,
					oldStatus, newStatus, oldResolution, newResolution,
					commentID, labelID, byParticipantID)
				if err != nil {
					return err
				}
			}
		}

		// Update tracker.next_ticket_id
		if maxTicketID != 0 {
			if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
				_, err := tx.ExecContext(ctx, `
					UPDATE tracker
					SET next_ticket_id = $2 + 1
					WHERE id = $1
				`, trackerID, maxTicketID)
				return err
			}); err != nil {
				return err
			}
		}
		return nil
	}); err != nil {
		return err
	}

	return nil
}

func convertStatus(status *string) *model.TicketStatus {
	if status == nil {
		return nil
	}
	*status = strings.ToUpper(*status)
	return (*model.TicketStatus)(status)
}

func convertStatusToInt(status *string) *int {
	if status == nil {
		statusInt := model.STATUS_REPORTED
		return &statusInt
	}
	*status = strings.ToUpper(*status)
	statusInt := (model.TicketStatus)(*status).ToInt()
	return &statusInt
}

func convertResolution(resolution *string) *model.TicketResolution {
	if resolution == nil {
		return nil
	}
	*resolution = strings.ToUpper(*resolution)
	return (*model.TicketResolution)(resolution)
}

func convertResolutionToInt(resolution *string) *int {
	if resolution == nil {
		resolutionInt := model.RESOLVED_UNRESOLVED
		return &resolutionInt
	}
	*resolution = strings.ToUpper(*resolution)
	resolutionInt := (model.TicketResolution)(*resolution).ToInt()
	return &resolutionInt
}

var eventTypeMap = map[string]int{
	"created":          model.EVENT_CREATED,
	"comment":          model.EVENT_COMMENT,
	"status_change":    model.EVENT_STATUS_CHANGE,
	"label_added":      model.EVENT_LABEL_ADDED,
	"label_removed":    model.EVENT_LABEL_REMOVED,
	"assigned_user":    model.EVENT_ASSIGNED_USER,
	"unassigned_user":  model.EVENT_UNASSIGNED_USER,
	"user_mentioned":   model.EVENT_USER_MENTIONED,
	"ticket_mentioned": model.EVENT_TICKET_MENTIONED,
}
