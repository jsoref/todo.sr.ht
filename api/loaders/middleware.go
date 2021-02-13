package loaders

//go:generate ./gen UsersByIDLoader int api/graph/model.User
//go:generate ./gen UsersByNameLoader string api/graph/model.User
//go:generate ./gen TrackersByIDLoader int api/graph/model.Tracker
//go:generate ./gen TrackersByNameLoader string api/graph/model.Tracker
//go:generate ./gen TrackersByOwnerNameLoader [2]string api/graph/model.Tracker
//go:generate ./gen CommentsByIDLoader int api/graph/model.Comment
//go:generate ./gen TicketsByIDLoader int api/graph/model.Ticket
//go:generate go run github.com/vektah/dataloaden ParticipantsByIDLoader int git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model.Entity

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/lib/pq"
	sq "github.com/Masterminds/squirrel"

	"git.sr.ht/~sircmpwn/core-go/auth"
	"git.sr.ht/~sircmpwn/core-go/database"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
)

var loadersCtxKey = &contextKey{"loaders"}

type contextKey struct {
	name string
}

type Loaders struct {
	UsersByID           UsersByIDLoader
	UsersByName         UsersByNameLoader
	TrackersByID        TrackersByIDLoader
	TrackersByName      TrackersByNameLoader
	TrackersByOwnerName TrackersByOwnerNameLoader
	TicketsByID         TicketsByIDLoader
	CommentsByID        CommentsByIDLoader
	ParticipantsByID    ParticipantsByIDLoader
}

func fetchUsersByID(ctx context.Context) func(ids []int) ([]*model.User, []error) {
	return func(ids []int) ([]*model.User, []error) {
		users := make([]*model.User, len(ids))
		if err := database.WithTx(ctx, &sql.TxOptions{
			Isolation: 0,
			ReadOnly: true,
		}, func (tx *sql.Tx) error {
			var (
				err  error
				rows *sql.Rows
			)
			query := database.
				Select(ctx, (&model.User{}).As(`u`)).
				From(`"user" u`).
				Where(sq.Expr(`u.id = ANY(?)`, pq.Array(ids)))
			if rows, err = query.RunWith(tx).QueryContext(ctx); err != nil {
				return err
			}
			defer rows.Close()

			usersByID := map[int]*model.User{}
			for rows.Next() {
				user := model.User{}
				if err := rows.Scan(database.Scan(ctx, &user)...); err != nil {
					return err
				}
				usersByID[user.ID] = &user
			}
			if err = rows.Err(); err != nil {
				return err
			}

			for i, id := range ids {
				users[i] = usersByID[id]
			}

			return nil
		}); err != nil {
			panic(err)
		}

		return users, nil
	}
}

func fetchUsersByName(ctx context.Context) func(names []string) ([]*model.User, []error) {
	return func(names []string) ([]*model.User, []error) {
		users := make([]*model.User, len(names))
		if err := database.WithTx(ctx, &sql.TxOptions{
			Isolation: 0,
			ReadOnly: true,
		}, func (tx *sql.Tx) error {
			var (
				err  error
				rows *sql.Rows
			)
			query := database.
				Select(ctx, (&model.User{}).As(`u`)).
				From(`"user" u`).
				Where(sq.Expr(`u.username = ANY(?)`, pq.Array(names)))
			if rows, err = query.RunWith(tx).QueryContext(ctx); err != nil {
				return err
			}
			defer rows.Close()

			usersByName := map[string]*model.User{}
			for rows.Next() {
				user := model.User{}
				if err := rows.Scan(database.Scan(ctx, &user)...); err != nil {
					return err
				}
				usersByName[user.Username] = &user
			}
			if err = rows.Err(); err != nil {
				return err
			}

			for i, name := range names {
				users[i] = usersByName[name]
			}

			return nil
		}); err != nil {
			panic(err)
		}

		return users, nil
	}
}

func fetchTrackersByID(ctx context.Context) func(ids []int) ([]*model.Tracker, []error) {
	return func(ids []int) ([]*model.Tracker, []error) {
		trackers := make([]*model.Tracker, len(ids))
		if err := database.WithTx(ctx, &sql.TxOptions{
			Isolation: 0,
			ReadOnly: true,
		}, func (tx *sql.Tx) error {
			var (
				err  error
				rows *sql.Rows
			)
			// TODO: Stash the ACL details in case they're useful later?
			auser := auth.ForContext(ctx)
			query := database.
				Select(ctx, (&model.Tracker{}).As(`t`)).
				From(`"tracker" t`).
				LeftJoin(`user_access ua ON ua.tracker_id = t.id`).
				Where(sq.And{
					sq.Expr(`t.id = ANY(?)`, pq.Array(ids)),
					sq.Or{
						sq.Expr(`t.owner_id = ?`, auser.UserID),
						sq.Expr(`t.default_user_perms > 0`),
						sq.And{
							sq.Expr(`ua.user_id = ?`, auser.UserID),
							sq.Expr(`ua.permissions > 0`),
						},
					},
				})
			if rows, err = query.RunWith(tx).QueryContext(ctx); err != nil {
				return err
			}
			defer rows.Close()

			trackersByID := map[int]*model.Tracker{}
			for rows.Next() {
				tracker := model.Tracker{}
				if err := rows.Scan(database.Scan(ctx, &tracker)...); err != nil {
					return err
				}
				trackersByID[tracker.ID] = &tracker
			}
			if err = rows.Err(); err != nil {
				return err
			}

			for i, id := range ids {
				trackers[i] = trackersByID[id]
			}

			return nil
		}); err != nil {
			panic(err)
		}

		return trackers, nil
	}
}

func fetchTrackersByName(ctx context.Context) func(names []string) ([]*model.Tracker, []error) {
	return func(names []string) ([]*model.Tracker, []error) {
		trackers := make([]*model.Tracker, len(names))
		if err := database.WithTx(ctx, &sql.TxOptions{
			Isolation: 0,
			ReadOnly: true,
		}, func (tx *sql.Tx) error {
			var (
				err  error
				rows *sql.Rows
			)
			auser := auth.ForContext(ctx)
			query := database.
				Select(ctx, (&model.Tracker{}).As(`t`)).
				From(`"tracker" t`).
				Where(sq.And{
					sq.Expr(`t.name = ANY(?)`, pq.Array(names)),
					sq.Expr(`t.owner_id = ?`, auser.UserID),
				})
			if rows, err = query.RunWith(tx).QueryContext(ctx); err != nil {
				return err
			}
			defer rows.Close()

			trackersByName := map[string]*model.Tracker{}
			for rows.Next() {
				tracker := model.Tracker{}
				if err := rows.Scan(database.Scan(ctx, &tracker)...); err != nil {
					return err
				}
				trackersByName[tracker.Name] = &tracker
			}
			if err = rows.Err(); err != nil {
				return err
			}

			for i, name := range names {
				trackers[i] = trackersByName[name]
			}

			return nil
		}); err != nil {
			panic(err)
		}

		return trackers, nil
	}
}

func fetchTrackersByOwnerName(ctx context.Context) func(tuples [][2]string) ([]*model.Tracker, []error) {
	return func(tuples [][2]string) ([]*model.Tracker, []error) {
		trackers := make([]*model.Tracker, len(tuples))
		if err := database.WithTx(ctx, &sql.TxOptions{
			Isolation: 0,
			ReadOnly: true,
		}, func (tx *sql.Tx) error {
			var (
				err        error
				rows       *sql.Rows
				ownerNames []string = make([]string, len(tuples))
			)
			for i, tuple := range tuples {
				ownerNames[i] = tuple[0] + "/" + tuple[1]
			}
			// TODO: Stash the ACL details in case they're useful later?
			auser := auth.ForContext(ctx)
			query := database.
				Select(ctx).
				Prefix(`WITH user_tracker AS (
					SELECT
						substring(un for position('/' in un)-1) AS owner,
						substring(un from position('/' in un)+1) AS tracker
					FROM unnest(?::text[]) un)`, pq.Array(ownerNames)).
				Columns(database.Columns(ctx, (&model.Tracker{}).As(`tr`))...).
				Columns(`u.username`).
				Distinct().
				From(`user_tracker ut`).
				Join(`"user" u on ut.owner = u.username`).
				Join(`"tracker" tr ON ut.tracker = tr.name
					AND u.id = tr.owner_id`).
				LeftJoin(`user_access ua ON ua.tracker_id = tr.id`).
				Where(sq.Or{
					sq.Expr(`tr.owner_id = ?`, auser.UserID),
					sq.Expr(`tr.default_user_perms > 0`),
					sq.And{
						sq.Expr(`ua.user_id = ?`, auser.UserID),
						sq.Expr(`ua.permissions > 0`),
					},
				})
			if rows, err = query.RunWith(tx).QueryContext(ctx); err != nil {
				return err
			}
			defer rows.Close()

			trackersByOwnerName := map[[2]string]*model.Tracker{}
			for rows.Next() {
				var ownerName string
				tracker := model.Tracker{}
				if err := rows.Scan(append(
					database.Scan(ctx, &tracker), &ownerName)...); err != nil {
					return err
				}
				trackersByOwnerName[[2]string{ownerName, tracker.Name}] = &tracker
			}
			if err = rows.Err(); err != nil {
				return err
			}

			for i, tuple := range tuples {
				trackers[i] = trackersByOwnerName[tuple]
			}

			return nil
		}); err != nil {
			panic(err)
		}

		return trackers, nil
	}
}

func fetchTicketsByID(ctx context.Context) func(ids []int) ([]*model.Ticket, []error) {
	return func(ids []int) ([]*model.Ticket, []error) {
		tickets := make([]*model.Ticket, len(ids))

		if err := database.WithTx(ctx, &sql.TxOptions{
			Isolation: 0,
			ReadOnly: true,
		}, func (tx *sql.Tx) error {
			var (
				err  error
				rows *sql.Rows
			)
			auser := auth.ForContext(ctx)
			query := database.
				Select(ctx, (&model.Ticket{}).As(`ti`)).
				From(`"ticket" ti`).
				Join(`"tracker" tr ON tr.id = ti.tracker_id`).
				LeftJoin(`user_access ua ON ua.tracker_id = tr.id`).
				Where(sq.And{
					sq.Expr(`ti.id = ANY(?)`, pq.Array(ids)),
					sq.Or{
						sq.Expr(`tr.owner_id = ?`, auser.UserID),
						sq.Expr(`tr.default_user_perms > 0`),
						sq.And{
							sq.Expr(`ua.user_id = ?`, auser.UserID),
							sq.Expr(`ua.permissions > 0`),
						},
					},
				})
			if rows, err = query.RunWith(tx).QueryContext(ctx); err != nil {
				return err
			}
			defer rows.Close()

			ticketsByID := map[int]*model.Ticket{}
			for rows.Next() {
				ticket := model.Ticket{}
				if err := rows.Scan(database.Scan(ctx, &ticket)...); err != nil {
					return err
				}
				ticketsByID[ticket.PKID] = &ticket
			}
			if err = rows.Err(); err != nil {
				return err
			}

			for i, id := range ids {
				tickets[i] = ticketsByID[id]
			}

			return nil
		}); err != nil {
			panic(err)
		}

		return tickets, nil
	}
}

// NOTICE: This does not do any ACL checks.
func fetchCommentsByID(ctx context.Context) func(ids []int) ([]*model.Comment, []error) {
	return func(ids []int) ([]*model.Comment, []error) {
		comments := make([]*model.Comment, len(ids))
		if err := database.WithTx(ctx, &sql.TxOptions{
			Isolation: 0,
			ReadOnly: true,
		}, func (tx *sql.Tx) error {
			var (
				err  error
				rows *sql.Rows
			)
			if rows, err = tx.QueryContext(ctx, `
				SELECT id, text, authenticity, superceeded_by_id
				FROM ticket_comment
				WHERE id = ANY($1)
			`, pq.Array(ids)); err != nil {
				return err
			}
			defer rows.Close()

			commentsByID := map[int]*model.Comment{}
			for rows.Next() {
				var authenticity int
				comment := model.Comment{}
				if err := rows.Scan(&comment.Database.ID,
					&comment.Database.Text, &authenticity,
					&comment.Database.SuperceededByID); err != nil {
					return err
				}
				switch authenticity {
				case model.AUTH_AUTHENTIC:
					comment.Database.Authenticity = model.AuthenticityAuthentic
				case model.AUTH_UNAUTHENTICATED:
					comment.Database.Authenticity = model.AuthenticityUnauthenticated
				case model.AUTH_TAMPERED:
					comment.Database.Authenticity = model.AuthenticityTampered
				default:
					panic(errors.New("database invariant broken"))
				}
				commentsByID[comment.Database.ID] = &comment
			}
			if err = rows.Err(); err != nil {
				return err
			}

			for i, id := range ids {
				comments[i] = commentsByID[id]
			}

			return nil
		}); err != nil {
			panic(err)
		}

		return comments, nil
	}
}

func fetchParticipantsByID(ctx context.Context) func(ids []int) ([]model.Entity, []error) {
	return func(ids []int) ([]model.Entity, []error) {
		entities := make([]model.Entity, len(ids))
		if err := database.WithTx(ctx, &sql.TxOptions{
			Isolation: 0,
			ReadOnly: true,
		}, func (tx *sql.Tx) error {
			var (
				err  error
				rows *sql.Rows
			)
			if rows, err = tx.QueryContext(ctx, `
					SELECT
						participant.id,
						participant_type,

						-- User fields:
						COALESCE("user".id, 0),
						COALESCE("user".created, now() at time zone 'utc'),
						COALESCE("user".updated, now() at time zone 'utc'),
						COALESCE("user".username, ''),
						COALESCE("user".email, ''),
						"user".url, "user".location, "user".bio,

						-- Email fields:
						COALESCE(participant.email, ''),
						participant.email_name,

						-- External user fields:
						COALESCE(participant.external_id, ''),
						participant.external_url
					FROM participant
					LEFT JOIN "user" on participant.user_id = "user".id
					WHERE participant.id = ANY($1)
			`, pq.Array(ids)); err != nil {
				return err
			}
			defer rows.Close()

			entitiesByID := map[int]model.Entity{}
			for rows.Next() {
				var (
					pid    int
					ptype  string
					entity model.Entity
					email  model.EmailAddress
					ext    model.ExternalUser
					user   model.User
				)

				if err := rows.Scan(&pid, &ptype, &user.ID, &user.Created,
					&user.Updated, &user.Username, &user.Email, &user.URL,
					&user.Location, &user.Bio, &email.Mailbox, &email.Name,
					&ext.ExternalID, &ext.ExternalURL); err != nil {

					if err == sql.ErrNoRows {
						return nil
					} else {
						return err
					}
				}

				switch (ptype) {
				case "user":
					entity = &user
				case "email":
					entity = &email
				case "external":
					entity = &ext
				default:
					panic(fmt.Errorf("Database invariant broken; invalid participant type for ID %d", pid))
				}

				entitiesByID[pid] = entity
			}

			if err = rows.Err(); err != nil {
				return err
			}

			for i, id := range ids {
				entities[i] = entitiesByID[id]
			}

			return nil
		}); err != nil {
			panic(err)
		}

		return entities, nil
	}
}

func Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx := context.WithValue(r.Context(), loadersCtxKey, &Loaders{
			UsersByID: UsersByIDLoader{
				maxBatch: 100,
				wait:     1 * time.Millisecond,
				fetch:    fetchUsersByID(r.Context()),
			},
			UsersByName: UsersByNameLoader{
				maxBatch: 100,
				wait:     1 * time.Millisecond,
				fetch:    fetchUsersByName(r.Context()),
			},
			TrackersByID: TrackersByIDLoader{
				maxBatch: 100,
				wait:     1 * time.Millisecond,
				fetch:    fetchTrackersByID(r.Context()),
			},
			TrackersByName: TrackersByNameLoader{
				maxBatch: 100,
				wait:     1 * time.Millisecond,
				fetch:    fetchTrackersByName(r.Context()),
			},
			TrackersByOwnerName: TrackersByOwnerNameLoader{
				maxBatch: 100,
				wait:     1 * time.Millisecond,
				fetch:    fetchTrackersByOwnerName(r.Context()),
			},
			TicketsByID: TicketsByIDLoader{
				maxBatch: 100,
				wait:     1 * time.Millisecond,
				fetch:    fetchTicketsByID(r.Context()),
			},
			CommentsByID: CommentsByIDLoader{
				maxBatch: 100,
				wait:     1 * time.Millisecond,
				fetch:    fetchCommentsByID(r.Context()),
			},
			ParticipantsByID: ParticipantsByIDLoader{
				maxBatch: 100,
				wait:     1 * time.Millisecond,
				fetch:    fetchParticipantsByID(r.Context()),
			},
		})
		r = r.WithContext(ctx)
		next.ServeHTTP(w, r)
	})
}

func ForContext(ctx context.Context) *Loaders {
	raw, ok := ctx.Value(loadersCtxKey).(*Loaders)
	if !ok {
		panic(errors.New("Invalid data loaders context"))
	}
	return raw
}
