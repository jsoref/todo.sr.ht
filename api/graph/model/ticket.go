package model

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strconv"
	"time"

	sq "github.com/Masterminds/squirrel"

	"git.sr.ht/~sircmpwn/core-go/database"
	"git.sr.ht/~sircmpwn/core-go/model"
)

type Ticket struct {
	ID           int       `json:"id"` // tracker-scoped ID
	Created      time.Time `json:"created"`
	Updated      time.Time `json:"updated"`
	Title        string    `json:"title"`
	Description  string    `json:"description"`

	PKID         int // global ID
	TrackerID    int
	TrackerName  string
	OwnerName    string
	SubmitterID  int

	authenticity int
	status       int
	resolution   int

	alias  string
	fields *database.ModelFields
}

func (t *Ticket) As(alias string) *Ticket {
	t.alias = alias
	return t
}

func (t *Ticket) Alias() string {
	return t.alias
}

func (t *Ticket) Table() string {
	return `"tracker"`
}

func (t *Ticket) Ref() string {
	return fmt.Sprintf("~%s/%s#%d", t.OwnerName, t.TrackerName, t.ID)
}

func (t *Ticket) Status() TicketStatus {
	return intToStatus(t.status)
}

func (t *Ticket) Resolution() TicketResolution {
	return intToResolution(t.resolution)
}

func (t *Ticket) Authenticity() Authenticity {
	return intToAuthenticity(t.authenticity)
}

func (t *Ticket) Fields() *database.ModelFields {
	if t.fields != nil {
		return t.fields
	}
	t.fields = &database.ModelFields{
		Fields: []*database.FieldMap{
			{ "created", "created", &t.Created },
			{ "updated", "updated", &t.Updated },
			{ "title", "title", &t.Title },
			{ "description", "description", &t.Description },
			{ "authenticity", "authenticity", &t.authenticity },
			{ "status", "status", &t.status },
			{ "resolution", "resolution", &t.resolution },
			{ "tracker.name", "ref", &t.TrackerName },
			{ `"user".username`, "ref", &t.OwnerName },

			// Always fetch:
			{ "id", "", &t.PKID },
			{ "scoped_id", "", &t.ID },
			{ "submitter_id", "", &t.SubmitterID },
			{ "tracker_id", "", &t.TrackerID },
		},
	}
	return t.fields
}

func (t *Ticket) Select(q sq.SelectBuilder) sq.SelectBuilder {
	return q.LeftJoin(fmt.Sprintf(`tracker on %s = tracker.id`,
			database.WithAlias(t.alias, "tracker_id"))).
		LeftJoin(`"user" on tracker.owner_id = "user".id`)
}

func (t *Ticket) QueryWithCursor(ctx context.Context, runner sq.BaseRunner,
	q sq.SelectBuilder, cur *model.Cursor) ([]*Ticket, *model.Cursor) {
	var (
		err  error
		rows *sql.Rows
	)

	if cur.Next != "" {
		next, _ := strconv.ParseInt(cur.Next, 10, 64)
		q = q.Where(database.WithAlias(t.alias, "id")+"<= ?", next)
	}
	q = q.
		OrderBy(database.WithAlias(t.alias, "scoped_id") + " DESC").
		Limit(uint64(cur.Count + 1))

	if rows, err = q.RunWith(runner).QueryContext(ctx); err != nil {
		panic(err)
	}
	defer rows.Close()

	var tickets []*Ticket
	for rows.Next() {
		var ticket Ticket
		if err := rows.Scan(database.Scan(ctx, &ticket)...); err != nil {
			panic(err)
		}
		tickets = append(tickets, &ticket)
	}

	if len(tickets) > cur.Count {
		cur = &model.Cursor{
			Count:  cur.Count,
			Next:   strconv.Itoa(tickets[len(tickets)-1].ID),
			Search: cur.Search,
		}
		tickets = tickets[:cur.Count]
	} else {
		cur = nil
	}

	return tickets, cur
}

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

const (
	AUTH_AUTHENTIC = 0
	AUTH_UNAUTHENTICATED = 1
	AUTH_TAMPERED = 2
)

func intToAuthenticity(auth int) Authenticity {
	switch auth {
	case AUTH_AUTHENTIC:
		return AuthenticityAuthentic
	case AUTH_UNAUTHENTICATED:
		return AuthenticityUnauthenticated
	case AUTH_TAMPERED:
		return AuthenticityTampered
	default:
		panic(errors.New("database invariant broken"))
	}
}
