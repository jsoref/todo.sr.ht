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
	ID      int       `json:"id"` // tracker-scoped ID
	Created time.Time `json:"created"`
	Updated time.Time `json:"updated"`
	Subject string    `json:"subject"`
	Body    *string   `json:"body"`

	PKID         int // global ID
	TrackerID    int
	TrackerName  string
	OwnerName    string
	SubmitterID  int

	RawAuthenticity int
	RawStatus       int
	RawResolution   int

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
	return TicketStatusFromInt(t.RawStatus)
}

func (t *Ticket) Resolution() TicketResolution {
	return TicketResolutionFromInt(t.RawResolution)
}

func (t *Ticket) Authenticity() Authenticity {
	return intToAuthenticity(t.RawAuthenticity)
}

func (t *Ticket) Fields() *database.ModelFields {
	if t.fields != nil {
		return t.fields
	}
	t.fields = &database.ModelFields{
		Fields: []*database.FieldMap{
			{ "created", "created", &t.Created },
			{ "updated", "updated", &t.Updated },
			{ "title", "subject", &t.Subject },
			{ "description", "body", &t.Body },
			{ "authenticity", "authenticity", &t.RawAuthenticity },
			{ "status", "status", &t.RawStatus },
			{ "resolution", "resolution", &t.RawResolution },
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
		q = q.Where(database.WithAlias(t.alias, "scoped_id")+"<= ?", next)
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
