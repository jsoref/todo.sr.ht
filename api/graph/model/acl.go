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

type ACL interface {
	IsACL()
}

type DefaultACL struct {
	Browse  bool `json:"browse"`
	Submit  bool `json:"submit"`
	Comment bool `json:"comment"`
	Edit    bool `json:"edit"`
	Triage  bool `json:"triage"`
}

func (DefaultACL) IsACL() {}

type DefaultACLs struct {
	Anonymous ACL `json:"anonymous"`
	Submitter ACL `json:"submitter"`
	LoggedIn  ACL `json:"logged_in"`
}

type TrackerACL struct {
	ID      int       `json:"id"`
	Created time.Time `json:"created"`
	Browse  bool      `json:"browse"`
	Submit  bool      `json:"submit"`
	Comment bool      `json:"comment"`
	Edit    bool      `json:"edit"`
	Triage  bool      `json:"triage"`

	TrackerID int
	UserID    int

	alias  string
	fields *database.ModelFields
}

func (TrackerACL) IsACL() {}

func (acl *TrackerACL) As(alias string) *TrackerACL {
	acl.alias = alias
	return acl
}

func (acl *TrackerACL) Alias() string {
	return acl.alias
}

func (acl *TrackerACL) Table() string {
	return `"user_access"`
}

func (acl *TrackerACL) Fields() *database.ModelFields {
	if acl.fields != nil {
		return acl.fields
	}
	acl.fields = &database.ModelFields{
		Fields: []*database.FieldMap{
			{ "id", "id", &acl.ID },
			{ "created", "created", &acl.Created },

			// Always fetch:
			{ "id", "", &acl.ID },
			{ "user_id", "", &acl.UserID },
			{ "tracker_id", "", &acl.TrackerID },
		},
	}
	return acl.fields
}

func (acl *TrackerACL) QueryWithCursor(ctx context.Context, runner sq.BaseRunner,
	q sq.SelectBuilder, cur *model.Cursor) ([]*TrackerACL, *model.Cursor) {
	var (
		err  error
		rows *sql.Rows
	)

	if cur.Next != "" {
		next, _ := strconv.ParseInt(cur.Next, 10, 64)
		q = q.Where(database.WithAlias(acl.alias, "id")+"<= ?", next)
	}
	q = q.
		Column(`permissions`).
		OrderBy(database.WithAlias(acl.alias, "id")).
		Limit(uint64(cur.Count + 1))

	if rows, err = q.RunWith(runner).QueryContext(ctx); err != nil {
		panic(err)
	}
	defer rows.Close()

	var acls []*TrackerACL
	for rows.Next() {
		var (
			acl    TrackerACL
			access int
		)
		if err := rows.Scan(append(
			database.Scan(ctx, &acl), &access)...); err != nil {
			panic(err)
		}
		acl.Browse = access & ACCESS_BROWSE != 0
		acl.Submit = access & ACCESS_SUBMIT != 0
		acl.Comment = access & ACCESS_COMMENT != 0
		acl.Edit = access & ACCESS_EDIT != 0
		acl.Triage = access & ACCESS_TRIAGE != 0
		acls = append(acls, &acl)
	}

	if len(acls) > cur.Count {
		cur = &model.Cursor{
			Count:  cur.Count,
			Next:   strconv.Itoa(acls[len(acls)-1].ID),
			Search: cur.Search,
		}
		acls = acls[:cur.Count]
	} else {
		cur = nil
	}

	return acls, cur
}
