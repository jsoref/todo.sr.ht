package model

import (
	"context"
	"database/sql"
	"errors"
	"strconv"
	"time"

	sq "github.com/Masterminds/squirrel"

	"git.sr.ht/~sircmpwn/core-go/database"
	"git.sr.ht/~sircmpwn/core-go/model"
)

type Event struct {
	ID      int       `json:"id"`
	Created time.Time `json:"created"`

	EventType     int
	ParticipantID int
	TicketID      int

	ByParticipantID *int
	CommentID       *int
	LabelID         *int
	FromTicketID    *int

	OldStatus     int
	OldResolution int
	NewStatus     int
	NewResolution int

	alias  string
	fields *database.ModelFields
}

const (
	AUTH_AUTHENTIC = 0
	AUTH_UNAUTHENTICATED = 1
	AUTH_TAMPERED = 2
)

type Created struct {
	EventType     EventType `json:"eventType"`
	TicketID      int
	ParticipantID int
}

func (Created) IsEventDetail() {}

type Comment struct {
	EventType     EventType `json:"eventType"`
	TicketID      int
	ParticipantID int

	Database struct {
		ID              int
		Text            string
		Authenticity    Authenticity
		SuperceededByID *int
	}
}

func (Comment) IsEventDetail() {}

const (
    STATUS_REPORTED = 0
    STATUS_CONFIRMED = 1
    STATUS_IN_PROGRESS = 2
    STATUS_PENDING = 4
    STATUS_RESOLVED = 8
)

func intToStatus(status int) TicketStatus {
	switch (status) {
	case STATUS_REPORTED:
		return TicketStatusReported
	case STATUS_CONFIRMED:
		return TicketStatusConfirmed
	case STATUS_IN_PROGRESS:
		return TicketStatusInProgress
	case STATUS_PENDING:
		return TicketStatusPending
	case STATUS_RESOLVED:
		return TicketStatusResolved
	default:
		panic(errors.New("database invariant broken"))
	}
}

const (
    RESOLVED_UNRESOLVED = 0
    RESOLVED_FIXED = 1
    RESOLVED_IMPLEMENTED = 2
    RESOLVED_WONT_FIX = 4
    RESOLVED_BY_DESIGN = 8
    RESOLVED_INVALID = 16
    RESOLVED_DUPLICATE = 32
    RESOLVED_NOT_OUR_BUG = 64
)

func intToResolution(resolution int) TicketResolution {
	switch (resolution) {
	case RESOLVED_UNRESOLVED:
		return TicketResolutionUnresolved
	case RESOLVED_FIXED:
		return TicketResolutionFixed
	case RESOLVED_IMPLEMENTED:
		return TicketResolutionImplemented
	case RESOLVED_WONT_FIX:
		return TicketResolutionWontFix
	case RESOLVED_BY_DESIGN:
		return TicketResolutionByDesign
	case RESOLVED_INVALID:
		return TicketResolutionInvalid
	case RESOLVED_DUPLICATE:
		return TicketResolutionDuplicate
	case RESOLVED_NOT_OUR_BUG:
		return TicketResolutionNotOurBug
	default:
		panic(errors.New("database invariant broken"))
	}
}

type StatusChange struct {
	EventType     EventType        `json:"eventType"`
	TicketID      int
	ParticipantID int

	OldStatus     TicketStatus     `json:"oldStatus"`
	NewStatus     TicketStatus     `json:"newStatus"`
	OldResolution TicketResolution `json:"oldResolution"`
	NewResolution TicketResolution `json:"newResolution"`
}

func (StatusChange) IsEventDetail() {}

const (
    EVENT_CREATED = 1
    EVENT_COMMENT = 2
    EVENT_STATUS_CHANGE = 4
    EVENT_LABEL_ADDED = 8
    EVENT_LABEL_REMOVED = 16
    EVENT_ASSIGNED_USER = 32
    EVENT_UNASSIGNED_USER = 64
    EVENT_USER_MENTIONED = 128
    EVENT_TICKET_MENTIONED = 256
)

func (ev *Event) Changes() []EventDetail {
	var changes []EventDetail

	if ev.EventType & EVENT_CREATED != 0 {
		changes = append(changes, Created{
			EventType:     EventTypeCreated,
			TicketID:      ev.TicketID,
			ParticipantID: ev.ParticipantID,
		})
	}

	if ev.EventType & EVENT_COMMENT != 0 {
		comment := Comment{
			EventType:     EventTypeComment,
			TicketID:      ev.TicketID,
			ParticipantID: ev.ParticipantID,
		}
		comment.Database.ID = *ev.CommentID
		changes = append(changes, comment)
	}

	if ev.EventType & EVENT_STATUS_CHANGE != 0 {
		changes = append(changes, StatusChange{
			EventType:     EventTypeStatusChange,
			TicketID:      ev.TicketID,
			ParticipantID: ev.ParticipantID,

			OldStatus:     intToStatus(ev.OldStatus),
			NewStatus:     intToStatus(ev.NewStatus),
			OldResolution: intToResolution(ev.OldResolution),
			NewResolution: intToResolution(ev.NewResolution),
		})
	}

	return changes
}

func (ev *Event) As(alias string) *Event {
	ev.alias = alias
	return ev
}

func (ev *Event) Alias() string {
	return ev.alias
}

func (ev *Event) Table() string {
	return `"event"`
}

func (ev *Event) Fields() *database.ModelFields {
	if ev.fields != nil {
		return ev.fields
	}
	ev.fields = &database.ModelFields{
		Fields: []*database.FieldMap{
			{ "id", "id", &ev.ID },
			{ "created", "created", &ev.Created },

			// Always fetch:
			{ "id", "", &ev.ID },
			{ "event_type", "", &ev.EventType },
			{ "participant_id", "", &ev.ParticipantID },
			{ "ticket_id", "", &ev.TicketID },
			{ "by_participant_id", "", &ev.ByParticipantID },
			{ "comment_id", "", &ev.CommentID },
			{ "label_id", "", &ev.LabelID },
			{ "from_ticket_id", "", &ev.FromTicketID },
			{ "old_status", "", &ev.OldStatus },
			{ "old_resolution", "", &ev.OldResolution },
			{ "new_status", "", &ev.NewStatus },
			{ "new_resolution", "", &ev.NewResolution },
		},
	}
	return ev.fields
}

func (ev *Event) QueryWithCursor(ctx context.Context, runner sq.BaseRunner,
	q sq.SelectBuilder, cur *model.Cursor) ([]*Event, *model.Cursor) {
	var (
		err  error
		rows *sql.Rows
	)

	if cur.Next != "" {
		next, _ := strconv.ParseInt(cur.Next, 10, 64)
		q = q.Where(database.WithAlias(ev.alias, "id")+"<= ?", next)
	}
	q = q.
		OrderBy(database.WithAlias(ev.alias, "id") + " DESC").
		Limit(uint64(cur.Count + 1))

	if rows, err = q.RunWith(runner).QueryContext(ctx); err != nil {
		panic(err)
	}
	defer rows.Close()

	var events []*Event
	for rows.Next() {
		var event Event
		if err := rows.Scan(database.Scan(ctx, &event)...); err != nil {
			panic(err)
		}
		events = append(events, &event)
	}

	if len(events) > cur.Count {
		cur = &model.Cursor{
			Count:  cur.Count,
			Next:   strconv.Itoa(events[len(events)-1].ID),
			Search: cur.Search,
		}
		events = events[:cur.Count]
	} else {
		cur = nil
	}

	return events, cur
}
