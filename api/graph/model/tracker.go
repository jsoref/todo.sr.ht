package model

import (
	"context"
	"database/sql"
	"strconv"
	"time"

	sq "github.com/Masterminds/squirrel"

	"git.sr.ht/~sircmpwn/core-go/database"
	"git.sr.ht/~sircmpwn/core-go/model"
)

type Tracker struct {
	ID          int           `json:"id"`
	Created     time.Time     `json:"created"`
	Updated     time.Time     `json:"updated"`
	Name        string        `json:"name"`
	Description *string       `json:"description"`
	DefaultACLs *DefaultACLs  `json:"defaultACLs"`

	OwnerID int

	alias  string
	fields *database.ModelFields
}

func (t *Tracker) As(alias string) *Tracker {
	t.alias = alias
	return t
}

func (t *Tracker) Alias() string {
	return t.alias
}

func (t *Tracker) Table() string {
	return `"tracker"`
}

func (t *Tracker) Fields() *database.ModelFields {
	if t.fields != nil {
		return t.fields
	}
	// TODO: Fetch ACLs
	t.fields = &database.ModelFields{
		Fields: []*database.FieldMap{
			{ "id", "id", &t.ID },
			{ "created", "created", &t.Created },
			{ "updated", "updated", &t.Updated },
			{ "name", "name", &t.Name },
			{ "description", "description", &t.Description },

			// Always fetch:
			{ "id", "", &t.ID },
			{ "owner_id", "", &t.OwnerID },
		},
	}
	return t.fields
}

func (t *Tracker) QueryWithCursor(ctx context.Context, runner sq.BaseRunner,
	q sq.SelectBuilder, cur *model.Cursor) ([]*Tracker, *model.Cursor) {
	var (
		err  error
		rows *sql.Rows
	)

	if cur.Next != "" {
		next, _ := strconv.ParseInt(cur.Next, 10, 64)
		q = q.Where(database.WithAlias(t.alias, "id")+"<= ?", next)
	}
	q = q.
		OrderBy(database.WithAlias(t.alias, "id")).
		Limit(uint64(cur.Count + 1))

	if rows, err = q.RunWith(runner).QueryContext(ctx); err != nil {
		panic(err)
	}
	defer rows.Close()

	var trackers []*Tracker
	for rows.Next() {
		var tracker Tracker
		if err := rows.Scan(database.Scan(ctx, &tracker)...); err != nil {
			panic(err)
		}
		trackers = append(trackers, &tracker)
	}

	if len(trackers) > cur.Count {
		cur = &model.Cursor{
			Count:  cur.Count,
			Next:   strconv.Itoa(trackers[len(trackers)-1].ID),
			Search: cur.Search,
		}
		trackers = trackers[:cur.Count]
	} else {
		cur = nil
	}

	return trackers, cur
}
