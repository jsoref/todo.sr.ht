package graph

import (
	"context"
	"database/sql"
	"strings"
	"text/template"

	"git.sr.ht/~sircmpwn/core-go/auth"
	"git.sr.ht/~sircmpwn/core-go/config"
	"git.sr.ht/~sircmpwn/core-go/email"
	"github.com/emersion/go-message/mail"
	sq "github.com/Masterminds/squirrel"

	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/loaders"
)

type NewTicketDetails struct {
	Body      *string
	Root      string
	TicketURL string
}

var newTicketTemplate = template.Must(template.New("new-ticket").Parse(
`{{.Body}}

-- 
View on the web: {{.Root}}{{.TicketURL}}`))

type TicketStatusDetails struct {
	Root       string
	TicketURL  string
	EventID    int
	Status     string
	Resolution string
}

var ticketStatusTemplate = template.Must(template.New("ticket-status").Parse(
`{{if eq .Status "RESOLVED"}}Ticket resolved: {{.Resolution}}{{end}}
-- 
View on the web: {{.Root}}{{.TicketURL}}#event-{{.EventID}}`))

type SubmitCommentDetails struct {
	Comment       string
	Root          string
	TicketURL     string
	EventID       int
	Status        string
	Resolution    string
	StatusUpdated bool
}

var submitCommentTemplate = template.Must(template.New("ticket-status").Parse(`
{{- if .StatusUpdated -}}
{{- if eq .Status "RESOLVED" -}}
Ticket resolved: {{.Resolution}}

{{else -}}
Ticket re-opened: {{.Status}}

{{end}}{{end -}}
{{.Comment }}

-- 
View on the web: {{.Root}}{{.TicketURL}}#event-{{.EventID}}`))

type EventBuilder struct {
	ctx         context.Context
	tx          *sql.Tx
	eventType   uint
	submitterID int
	tracker     *model.Tracker
	ticket      *model.Ticket

	mentionedParticipants []int
	mentions *Mentions
}

// Creates a new event builder for a given submitter (a participant ID) and a
// certain event type, using the provided context and transaction. This is used
// to provide a common implementation for creating events and notifications,
// building up the list of implicated participants over time.
//
// The order in which you call the subsequent functions is important:
// 1. WithTicket
// 2. AddMentions
// 3. InsertSubscriptions
// 4. InsertNotifications
func NewEventBuilder(ctx context.Context, tx *sql.Tx,
	submitterID int, eventType uint) *EventBuilder {
	// Create a temporary table of all participants affected by this
	// submission. This includes everyone who will be notified about it.
	_, err := tx.ExecContext(ctx, `
		CREATE TEMP TABLE event_participant
		ON COMMIT DROP
		AS (SELECT
			-- The affected participant:
			$1::INTEGER AS participant_id,
			-- Events they should be notified of:
			$2::INTEGER AS event_type,
			-- Should they be subscribed to this ticket?
			true AS subscribe
		);
	`, submitterID, eventType)
	if err != nil {
		panic(err)
	}

	return &EventBuilder{
		ctx:         ctx,
		tx:          tx,
		eventType:   eventType,
		submitterID: submitterID,
	}
}

// Associates this event with a ticket and implicates the submitter for the
// appropriate events and notifications.
func (builder *EventBuilder) WithTicket(
	tracker *model.Tracker, ticket *model.Ticket) *EventBuilder {
	builder.tracker = tracker
	builder.ticket = ticket
	_, err := builder.tx.ExecContext(builder.ctx, `
		INSERT INTO event_participant (
			participant_id, event_type, subscribe
		)
		SELECT sub.participant_id, $1, false
		FROM ticket_subscription sub
		WHERE sub.tracker_id = $2 OR sub.ticket_id = $3
	`, builder.eventType, tracker.ID, ticket.PKID)
	if err != nil {
		panic(err)
	}
	return builder
}

// Adds mentions to this event builder
func (builder *EventBuilder) AddMentions(mentions *Mentions) {
	builder.mentions = mentions
	for user, _ := range mentions.Users {
		part, err := loaders.ForContext(builder.ctx).ParticipantsByUsername.Load(user)
		if err != nil {
			panic(err)
		}
		if part == nil {
			continue
		}
		_, err = builder.tx.ExecContext(builder.ctx, `
			INSERT INTO event_participant (
				participant_id, event_type, subscribe
			) VALUES (
				$1, $2, true
			);
		`, part.ID, model.EVENT_USER_MENTIONED)
		if err != nil {
			panic(err)
		}
		builder.mentionedParticipants = append(builder.mentionedParticipants, part.ID)
	}
}

// Creates subscriptions for all affected users
func (builder *EventBuilder) InsertSubscriptions() {
	_, err := builder.tx.ExecContext(builder.ctx, `
		INSERT INTO ticket_subscription (
			created, updated, ticket_id, participant_id
		)
		SELECT
			NOW() at time zone 'utc',
			NOW() at time zone 'utc',
			$1, participant_id
		FROM event_participant
		WHERE subscribe = true
		ON CONFLICT ON CONSTRAINT subscription_ticket_participant_uq
		DO NOTHING;
	`, builder.ticket.PKID)
	if err != nil {
		panic(err)
	}
}

// Adds event_notification records for all affected users and inserts
// ancillary events (such as mentions) and their notifications.
func (builder *EventBuilder) InsertNotifications(eventID int, commentID *int) {
	_, err := builder.tx.ExecContext(builder.ctx, `
		INSERT INTO event_notification (created, event_id, user_id)
		SELECT
			NOW() at time zone 'utc',
			$1, part.user_id
		FROM event_participant ev
		JOIN participant part ON part.id = ev.participant_id
		WHERE part.user_id IS NOT NULL AND ev.event_type = $2;
	`, eventID, builder.eventType)
	if err != nil {
		panic(err)
	}

	if builder.mentions == nil {
		return
	}

	for _, id := range builder.mentionedParticipants {
		var eventID int
		row := builder.tx.QueryRowContext(builder.ctx, `
			INSERT INTO event (
				created, event_type, participant_id, by_participant_id,
				ticket_id, from_ticket_id, comment_id
			) VALUES (
				NOW() at time zone 'utc',
				$1, $2, $3, $4, $4, $5
			) RETURNING id;`,
			model.EVENT_USER_MENTIONED, id, builder.submitterID,
			builder.ticket.PKID, commentID)
		if err := row.Scan(&eventID); err != nil {
			panic(err)
		}
		_, err := builder.tx.ExecContext(builder.ctx, `
			INSERT INTO event_notification (created, event_id, user_id)
			SELECT
				NOW() at time zone 'utc',
				$1, part.user_id
			FROM event_participant ev
			JOIN participant part ON part.id = ev.participant_id
			WHERE part.user_id IS NOT NULL AND ev.event_type = $2;
		`, eventID, model.EVENT_USER_MENTIONED)
		if err != nil {
			panic(err)
		}
	}

	for _, target := range builder.mentions.Tickets {
		_, err := builder.tx.ExecContext(builder.ctx, `
			WITH target AS (
				SELECT tk.id
				FROM ticket tk
				JOIN tracker tr ON tk.tracker_id = tr.id
				JOIN "user" u ON u.id = tr.owner_id
				WHERE u.username = $1 AND tr.name = $2 AND tk.scoped_id = $3
			)
			INSERT INTO event (
				created, event_type, by_participant_id, ticket_id,
				from_ticket_id, comment_id
			) VALUES (
				NOW() at time zone 'utc',
				$4, $5, (SELECT id FROM target), $6, $7
			)`,
			target.OwnerName, target.TrackerName, target.ID,
			model.EVENT_TICKET_MENTIONED, builder.submitterID,
			builder.ticket.PKID, commentID)
		if err != nil {
			panic(err)
		}
	}
}

func (builder *EventBuilder) SendEmails(subject string,
	template *template.Template, context interface{}) {
	var (
		rcpts []mail.Address
		notifySelf, copiedSelf bool
	)

	user := auth.ForContext(builder.ctx)
	row := builder.tx.QueryRowContext(builder.ctx, `
		SELECT notify_self FROM "user" WHERE id = $1
	`, user.UserID)
	if err := row.Scan(&notifySelf); err != nil {
		panic(err)
	}

	// XXX: It may be possible to implement this more efficiently by skipping
	// the joins and pre-stashing the email details when inserting
	// event_participants.
	subs := sq.Select(`
			CASE part.participant_type
			WHEN 'user' THEN '~' || "user".username
			WHEN 'email' THEN part.email_name
			ELSE null END
		`, `
			CASE part.participant_type
			WHEN 'user' THEN "user".email
			WHEN 'email' THEN part.email
			ELSE null END
		`).
		Distinct().
		From(`event_participant evpart`).
		Join(`participant part ON evpart.participant_id = part.id`).
		LeftJoin(`"user" ON "user".id = part.user_id`)
	rows, err := subs.
		PlaceholderFormat(sq.Dollar).
		RunWith(builder.tx).
		QueryContext(builder.ctx)
	if err != nil && err != sql.ErrNoRows {
		panic(err)
	}

	set := make(map[string]interface{})
	for rows.Next() {
		var name, address string
		if err := rows.Scan(&name, &address); err != nil {
			panic(err)
		}
		if address == user.Email {
			if notifySelf {
				copiedSelf = true
			} else {
				continue
			}
		}
		if _, ok := set[address]; ok {
			continue
		}
		set[address] = nil
		rcpts = append(rcpts, mail.Address{
			Name: name,
			Address: address,
		})
	}
	if notifySelf && !copiedSelf {
		rcpts = append(rcpts, mail.Address{
			Name: "~" + user.Username,
			Address: user.Email,
		})
	}

	var body strings.Builder
	err = template.Execute(&body, context)
	if err != nil {
		panic(err)
	}

	conf := config.ForContext(builder.ctx)
	var notifyFrom string
	if addr, ok := conf.Get("todo.sr.ht", "notify-from"); ok {
		notifyFrom = addr
	} else if addr, ok := conf.Get("mail", "smtp-from"); ok {
		notifyFrom = addr
	} else {
		panic("Invalid mail configuratiojn")
	}

	from := mail.Address{
		Name: "~" + user.Username,
		Address: notifyFrom,
	}
	for _, rcpt := range rcpts {
		var header mail.Header
		// TODO: Add these headers:
		// - In-Reply-To
		// - Reply-To
		// - Sender
		// - List-Unsubscribe
		header.SetAddressList("To", []*mail.Address{&rcpt})
		header.SetAddressList("From", []*mail.Address{&from})
		header.SetSubject(subject)

		// TODO: Fetch user PGP key (or send via meta.sr.ht API?)
		err = email.EnqueueStd(builder.ctx, header,
			strings.NewReader(body.String()), nil)
		if err != nil {
			panic(err)
		}
	}
}
