package graph

import (
	"context"
	"database/sql"
	"regexp"
	"strings"
	"text/template"

	"git.sr.ht/~sircmpwn/core-go/auth"
	"git.sr.ht/~sircmpwn/core-go/email"
	"github.com/emersion/go-message/mail"
	sq "github.com/Masterminds/squirrel"

	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
)

//go:generate go run github.com/99designs/gqlgen

type Resolver struct{}

var (
	trackerNameRE = regexp.MustCompile(`^[A-Za-z0-9._-]+$`)

	newTicketTemplate = template.Must(template.New("new-ticket").Parse(`{{.Body}}

-- 
View on the web: {{.Root}}{{.TicketURL}}`))
)

type NewTicketDetails struct {
	Body      *string
	Root      string
	TicketURL string
}

func aclBits(input model.ACLInput) uint {
		var bits uint
		if input.Browse {
			bits |= model.ACCESS_BROWSE
		}
		if input.Submit {
			bits |= model.ACCESS_SUBMIT
		}
		if input.Comment {
			bits |= model.ACCESS_COMMENT
		}
		if input.Edit {
			bits |= model.ACCESS_EDIT
		}
		if input.Triage {
			bits |= model.ACCESS_TRIAGE
		}
		return bits
}

func queueNotifications(ctx context.Context, tx *sql.Tx, subject string,
	template *template.Template, context interface{},
	subscribers sq.SelectBuilder) {
	var (
		rcpts []mail.Address
		notifySelf, copiedSelf bool
	)

	user := auth.ForContext(ctx)
	row := tx.QueryRowContext(ctx, `
		SELECT notify_self FROM "user" WHERE id = $1
	`, user.UserID)
	if err := row.Scan(&notifySelf); err != nil {
		panic(err)
	}

	rows, err := subscribers.
		PlaceholderFormat(sq.Dollar).
		RunWith(tx).
		QueryContext(ctx)
	if err != nil && err != sql.ErrNoRows {
		panic(err)
	}

	for rows.Next() {
		var name, address string
		if err := rows.Scan(&name, &address); err != nil {
			panic(err)
		}
		if address == user.Email {
			if notifySelf {
				copiedSelf = true
			} else {
				break
			}
		}
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

	for _, rcpt := range rcpts {
		var header mail.Header
		header.SetAddressList("To", []*mail.Address{&rcpt})
		header.SetSubject(subject)

		// TODO: Fetch user PGP key (or send via meta.sr.ht API?)
		err = email.EnqueueStd(ctx, header,
			strings.NewReader(body.String()), nil)
		if err != nil {
			panic(err)
		}
	}
}
