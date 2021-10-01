package graph

// This file will be automatically regenerated based on the schema, any resolver implementations
// will be copied through when generating and any unknown code will be moved to the end.

import (
	"context"
	"database/sql"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"

	"git.sr.ht/~sircmpwn/core-go/auth"
	"git.sr.ht/~sircmpwn/core-go/database"
	coremodel "git.sr.ht/~sircmpwn/core-go/model"
	"git.sr.ht/~sircmpwn/core-go/valid"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/api"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/loaders"
	"github.com/99designs/gqlgen/graphql"
	sq "github.com/Masterminds/squirrel"
	"github.com/lib/pq"
)

func (r *assignmentResolver) Ticket(ctx context.Context, obj *model.Assignment) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *assignmentResolver) Assigner(ctx context.Context, obj *model.Assignment) (model.Entity, error) {
	return loaders.ForContext(ctx).ParticipantsByID.Load(obj.AssignerID)
}

func (r *assignmentResolver) Assignee(ctx context.Context, obj *model.Assignment) (model.Entity, error) {
	return loaders.ForContext(ctx).ParticipantsByID.Load(obj.AssigneeID)
}

func (r *commentResolver) Ticket(ctx context.Context, obj *model.Comment) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *commentResolver) Author(ctx context.Context, obj *model.Comment) (model.Entity, error) {
	return loaders.ForContext(ctx).ParticipantsByID.Load(obj.ParticipantID)
}

func (r *commentResolver) Text(ctx context.Context, obj *model.Comment) (string, error) {
	// The only route to this resolver is via event details, which is already
	// authenticated. Further access to other resources is limited to
	// authenticated routes, such as TicketByID.
	comment, err := loaders.ForContext(ctx).CommentsByIDUnsafe.Load(obj.Database.ID)
	return comment.Database.Text, err
}

func (r *commentResolver) Authenticity(ctx context.Context, obj *model.Comment) (model.Authenticity, error) {
	// The only route to this resolver is via event details, which is already
	// authenticated. Further access to other resources is limited to
	// authenticated routes, such as TicketByID.
	comment, err := loaders.ForContext(ctx).CommentsByIDUnsafe.Load(obj.Database.ID)
	return comment.Database.Authenticity, err
}

func (r *commentResolver) SupersededBy(ctx context.Context, obj *model.Comment) (*model.Comment, error) {
	if obj.Database.SuperceededByID == nil {
		return nil, nil
	}
	// The only route to this resolver is via event details, which is already
	// authenticated. Further access to other resources is limited to
	// authenticated routes, such as TicketByID.
	return loaders.ForContext(ctx).CommentsByIDUnsafe.Load(*obj.Database.SuperceededByID)
}

func (r *createdResolver) Ticket(ctx context.Context, obj *model.Created) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *createdResolver) Author(ctx context.Context, obj *model.Created) (model.Entity, error) {
	return loaders.ForContext(ctx).ParticipantsByID.Load(obj.ParticipantID)
}

func (r *eventResolver) Ticket(ctx context.Context, obj *model.Event) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *labelResolver) Tracker(ctx context.Context, obj *model.Label) (*model.Tracker, error) {
	return loaders.ForContext(ctx).TrackersByID.Load(obj.TrackerID)
}

func (r *labelResolver) Tickets(ctx context.Context, obj *model.Label, cursor *coremodel.Cursor) (*model.TicketCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var tickets []*model.Ticket
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		// No authentication necessary: if you have access to the label you
		// have access to the tickets.
		ticket := (&model.Ticket{}).As(`tk`)
		query := database.
			Select(ctx, ticket).
			From(`ticket tk`).
			Join(`ticket_label tl ON tl.ticket_id = tk.id`).
			Where(`tl.label_id = ?`, obj.ID)
		tickets, cursor = ticket.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.TicketCursor{tickets, cursor}, nil
}

func (r *labelUpdateResolver) Ticket(ctx context.Context, obj *model.LabelUpdate) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *labelUpdateResolver) Labeler(ctx context.Context, obj *model.LabelUpdate) (model.Entity, error) {
	return loaders.ForContext(ctx).ParticipantsByID.Load(obj.ParticipantID)
}

func (r *labelUpdateResolver) Label(ctx context.Context, obj *model.LabelUpdate) (*model.Label, error) {
	return loaders.ForContext(ctx).LabelsByID.Load(obj.LabelID)
}

func (r *mutationResolver) CreateTracker(ctx context.Context, name string, description *string, visibility model.Visibility, importArg *graphql.Upload) (*model.Tracker, error) {
	valid := valid.New(ctx)
	valid.Expect(trackerNameRE.MatchString(name), "Name must match %s", trackerNameRE.String()).
		WithField("name").
		And(name != "." && name != ".." && name != ".git" && name != ".hg",
			"This is a reserved name and cannot be used for user trakcers.").
		WithField("name")
	// TODO: Unify description limits
	valid.Expect(description == nil || len(*description) < 8192,
		"Description must be fewer than 8192 characters").
		WithField("description")
	valid.Expect(importArg == nil, "TODO: imports").WithField("import") // TODO
	if !valid.Ok() {
		return nil, nil
	}

	var tracker model.Tracker
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		user := auth.ForContext(ctx)
		row := tx.QueryRowContext(ctx, `
			INSERT INTO tracker (
				created, updated,
				owner_id, name, description, visibility
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				$1, $2, $3, $4
			)
			RETURNING
				id, owner_id, created, updated, name, description, visibility;
		`, user.UserID, name, description, visibility.String())

		if err := row.Scan(&tracker.ID, &tracker.OwnerID, &tracker.Created,
			&tracker.Updated, &tracker.Name, &tracker.Description,
			&tracker.Visibility); err != nil {
			if err, ok := err.(*pq.Error); ok &&
				err.Code == "23505" && // unique_violation
				err.Constraint == "tracker_owner_id_name_unique" {
				valid.Error("A tracker by this name already exists.").
					WithField("name")
				return errors.New("placeholder") // To rollback the transaction
			}
			return err
		}
		tracker.Access = model.ACCESS_ALL

		_, err := tx.ExecContext(ctx, `
			WITH part AS (
				INSERT INTO participant (
					created, participant_type, user_id
				) VALUES (
					NOW() at time zone 'utc',
					'user', $1
				)
				ON CONFLICT ON CONSTRAINT participant_user_id_key
				DO UPDATE SET created = participant.created
				RETURNING id
			) INSERT INTO ticket_subscription (
				created, updated, tracker_id, participant_id
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				$2, (SELECT id FROM part)
			);
		`, user.UserID, tracker.ID)
		return err
	}); err != nil {
		if !valid.Ok() {
			return nil, nil
		}
		return nil, err
	}

	return &tracker, nil
}

func (r *mutationResolver) UpdateTracker(ctx context.Context, id int, input map[string]interface{}) (*model.Tracker, error) {
	valid := valid.New(ctx).WithInput(input)

	valid.OptionalString("description", func(desc string) {
		valid.Expect(len(desc) < 8192,
			"Description must be fewer than 8192 characters").
			WithField("description")
	})
	valid.OptionalString("visibility", func(vis string) {
		input["visibility"] = model.Visibility(vis)
	})
	if !valid.Ok() {
		return nil, nil
	}

	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(id)
	if err != nil || tracker == nil {
		return nil, err
	}
	if tracker.OwnerID != auth.ForContext(ctx).UserID {
		return nil, fmt.Errorf("Access denied")
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		var err error
		if len(input) != 0 {
			_, err = database.Apply(tracker, input).
				Where(database.WithAlias(tracker.Alias(), `id`)+"= ?", tracker.ID).
				Set(database.WithAlias(tracker.Alias(), `updated`),
					sq.Expr(`now() at time zone 'utc'`)).
				RunWith(tx).
				ExecContext(ctx)
		}
		return err
	}); err != nil {
		return nil, err
	}

	return tracker, nil
}

func (r *mutationResolver) DeleteTracker(ctx context.Context, id int) (*model.Tracker, error) {
	var tracker model.Tracker
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		user := auth.ForContext(ctx)
		row := tx.QueryRowContext(ctx, `
			DELETE FROM tracker
			WHERE id = $1 AND owner_id = $2
			RETURNING
				id, owner_id, created, updated, name, description, visibility;
		`, id, user.UserID)

		if err := row.Scan(&tracker.ID, &tracker.OwnerID, &tracker.Created,
			&tracker.Updated, &tracker.Name, &tracker.Description,
			&tracker.Visibility); err != nil {
			return err
		}
		tracker.Access = model.ACCESS_ALL
		return nil
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	return &tracker, nil
}

func (r *mutationResolver) UpdateUserACL(ctx context.Context, trackerID int, userID int, input model.ACLInput) (*model.TrackerACL, error) {
	var acl model.TrackerACL
	bits := aclBits(input)
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		user := auth.ForContext(ctx)
		row := tx.QueryRowContext(ctx, `
			INSERT INTO user_access (
				created, tracker_id, user_id, permissions
			) VALUES (
				NOW() at time zone 'utc',
				-- The purpose of this is to filter out tracker that the user is
				-- not an owner of. Saves us a round-trip
				(SELECT id FROM tracker WHERE id = $1 AND owner_id = $4),
				$2, $3
			)
			ON CONFLICT ON CONSTRAINT idx_useraccess_tracker_user_unique
			DO UPDATE SET permissions = $3
			RETURNING id, created, tracker_id, user_id;
		`, trackerID, userID, bits, user.UserID)

		if err := row.Scan(&acl.ID, &acl.Created, &acl.TrackerID,
			&acl.UserID); err != nil {
			return err
		}

		acl.Browse = bits&model.ACCESS_BROWSE != 0
		acl.Submit = bits&model.ACCESS_SUBMIT != 0
		acl.Comment = bits&model.ACCESS_COMMENT != 0
		acl.Edit = bits&model.ACCESS_EDIT != 0
		acl.Triage = bits&model.ACCESS_TRIAGE != 0
		return nil
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	return &acl, nil
}

func (r *mutationResolver) UpdateTrackerACL(ctx context.Context, trackerID int, input model.ACLInput) (*model.DefaultACL, error) {
	bits := aclBits(input)
	user := auth.ForContext(ctx)
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `
			UPDATE tracker
			SET default_access = $1
			WHERE id = $2 AND owner_id = $3;
		`, bits, trackerID, user.UserID)
		return err
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	return &model.DefaultACL{
		bits&model.ACCESS_BROWSE != 0,
		bits&model.ACCESS_SUBMIT != 0,
		bits&model.ACCESS_COMMENT != 0,
		bits&model.ACCESS_EDIT != 0,
		bits&model.ACCESS_TRIAGE != 0,
	}, nil
}

func (r *mutationResolver) DeleteACL(ctx context.Context, id int) (*model.TrackerACL, error) {
	var acl model.TrackerACL
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		user := auth.ForContext(ctx)
		row := tx.QueryRowContext(ctx, `
			DELETE FROM user_access ua
			USING tracker
			WHERE
				ua.tracker_id = tracker.id AND
				ua.id = $1 AND
				tracker.owner_id = $2
			RETURNING ua.id, ua.created, ua.tracker_id, ua.user_id, ua.permissions;
		`, id, user.UserID)

		var bits uint
		if err := row.Scan(&acl.ID, &acl.Created, &acl.TrackerID,
			&acl.UserID, &bits); err != nil {
			return err
		}

		acl.Browse = bits&model.ACCESS_BROWSE != 0
		acl.Submit = bits&model.ACCESS_SUBMIT != 0
		acl.Comment = bits&model.ACCESS_COMMENT != 0
		acl.Edit = bits&model.ACCESS_EDIT != 0
		acl.Triage = bits&model.ACCESS_TRIAGE != 0
		return nil
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	return &acl, nil
}

func (r *mutationResolver) TrackerSubscribe(ctx context.Context, trackerID int) (*model.TrackerSubscription, error) {
	var sub model.TrackerSubscription
	user := auth.ForContext(ctx)
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			WITH part AS (
				INSERT INTO participant (
					created, participant_type, user_id
				) VALUES (
					NOW() at time zone 'utc',
					'user', $1
				)
				ON CONFLICT ON CONSTRAINT participant_user_id_key
				DO UPDATE SET created = participant.created
				RETURNING id
			), tk AS (
				SELECT tracker.id
				FROM tracker
				LEFT JOIN user_access ua ON ua.tracker_id = tracker.id
				WHERE tracker.id = $2 AND (
					owner_id = $1 OR
					visibility != 'PRIVATE' OR
					(ua.user_id = $1 AND ua.permissions > 0)
				)
			) INSERT INTO ticket_subscription (
				created, updated, tracker_id, participant_id
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				(SELECT id FROM tk),
				(SELECT id FROM part)
			)
			ON CONFLICT ON CONSTRAINT subscription_tracker_participant_uq
			DO UPDATE SET updated = NOW() at time zone 'utc'
			RETURNING id, created, tracker_id;
		`, user.UserID, trackerID)
		return row.Scan(&sub.ID, &sub.Created, &sub.TrackerID)
	}); err != nil {
		return nil, err
	}
	return &sub, nil
}

func (r *mutationResolver) TrackerUnsubscribe(ctx context.Context, trackerID int, tickets bool) (*model.TrackerSubscription, error) {
	var sub model.TrackerSubscription
	user := auth.ForContext(ctx)
	if tickets {
		panic("not implemented")
	}
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			WITH part AS (
				INSERT INTO participant (
					created, participant_type, user_id
				) VALUES (
					NOW() at time zone 'utc',
					'user', $1
				)
				ON CONFLICT ON CONSTRAINT participant_user_id_key
				DO UPDATE SET created = participant.created
				RETURNING id
			)
			DELETE FROM ticket_subscription
			WHERE tracker_id = $2 AND participant_id = (SELECT id FROM part)
			RETURNING id, created, tracker_id;
		`, user.UserID, trackerID)
		return row.Scan(&sub.ID, &sub.Created, &sub.TrackerID)
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	return &sub, nil
}

func (r *mutationResolver) TicketSubscribe(ctx context.Context, trackerID int, ticketID int) (*model.TicketSubscription, error) {
	var sub model.TicketSubscription
	user := auth.ForContext(ctx)
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			WITH part AS (
				INSERT INTO participant (
					created, participant_type, user_id
				) VALUES (
					NOW() at time zone 'utc',
					'user', $1
				)
				ON CONFLICT ON CONSTRAINT participant_user_id_key
				DO UPDATE SET created = participant.created
				RETURNING id
			), tk AS (
				SELECT ticket.id
				FROM ticket
				JOIN tracker ON tracker.id = ticket.tracker_id
				LEFT JOIN user_access ua ON ua.tracker_id = tracker.id
				WHERE ticket.tracker_id = $2 AND ticket.scoped_id = $3 AND (
					owner_id = $1 OR
					visibility != 'PRIVATE' OR
					(ua.user_id = $1 AND ua.permissions > 0)
				)
			) INSERT INTO ticket_subscription (
				created, updated, ticket_id, participant_id
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				(SELECT id FROM tk),
				(SELECT id FROM part)
			)
			ON CONFLICT ON CONSTRAINT subscription_ticket_participant_uq
			DO UPDATE SET updated = NOW() at time zone 'utc'
			RETURNING id, created, ticket_id;
		`, user.UserID, trackerID, ticketID)
		return row.Scan(&sub.ID, &sub.Created, &sub.TicketID)
	}); err != nil {
		return nil, err
	}
	return &sub, nil
}

func (r *mutationResolver) TicketUnsubscribe(ctx context.Context, trackerID int, ticketID int) (*model.TicketSubscription, error) {
	var sub model.TicketSubscription
	user := auth.ForContext(ctx)
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			WITH part AS (
				INSERT INTO participant (
					created, participant_type, user_id
				) VALUES (
					NOW() at time zone 'utc',
					'user', $1
				)
				ON CONFLICT ON CONSTRAINT participant_user_id_key
				DO UPDATE SET created = participant.created
				RETURNING id
			), tk AS (
				SELECT ticket.id
				FROM ticket
				JOIN tracker ON tracker.id = ticket.tracker_id
				WHERE tracker.id = $2 AND ticket.scoped_id = $3
			)
			DELETE FROM ticket_subscription
			WHERE
				ticket_id = (SELECT id FROM tk) AND
				participant_id = (SELECT id FROM part)
			RETURNING id, created, ticket_id;
		`, user.UserID, trackerID, ticketID)
		return row.Scan(&sub.ID, &sub.Created, &sub.TicketID)
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	return &sub, nil
}

func (r *mutationResolver) CreateLabel(ctx context.Context, trackerID int, name string, foreground string, background string) (*model.Label, error) {
	var label model.Label
	user := auth.ForContext(ctx)
	var (
		fgb [3]byte
		bgb [3]byte
	)
	if !strings.HasPrefix(foreground, "#") {
		return nil, fmt.Errorf("Invalid foreground color format")
	}
	if n, err := hex.Decode(fgb[:], []byte(foreground[1:])); err != nil || n != 3 {
		return nil, fmt.Errorf("Invalid foreground color format")
	}
	if !strings.HasPrefix(background, "#") {
		return nil, fmt.Errorf("Invalid background color format")
	}
	if n, err := hex.Decode(bgb[:], []byte(background[1:])); err != nil || n != 3 {
		return nil, fmt.Errorf("Invalid background color format")
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		// TODO: Rename the columns for consistency
		row := tx.QueryRowContext(ctx, `
			WITH tr AS (
				SELECT id
				FROM tracker
				WHERE id = $1 AND owner_id = $2
			) INSERT INTO label (
				created, updated, tracker_id, name, color, text_color
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				(SELECT id FROM tr),
				$3, $4, $5
			) RETURNING id, created, name, color, text_color, tracker_id;
		`, trackerID, user.UserID, name, background, foreground)

		if err := row.Scan(&label.ID, &label.Created, &label.Name,
			&label.BackgroundColor, &label.ForegroundColor,
			&label.TrackerID); err != nil {
			if err, ok := err.(*pq.Error); ok &&
				err.Code == "23505" && // unique_violation
				err.Constraint == "idx_tracker_name_unique" {
				return fmt.Errorf("A label by this name already exists")
			}
			// XXX: This is not ideal
			if err, ok := err.(*pq.Error); ok &&
				err.Code == "23502" { // not_null_violation
				return sql.ErrNoRows
			}
			return err
		}
		return nil
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	return &label, nil
}

func (r *mutationResolver) UpdateLabel(ctx context.Context, id int, input map[string]interface{}) (*model.Label, error) {
	valid := valid.New(ctx).WithInput(input)
	var (
		fgb [3]byte
		bgb [3]byte
	)
	valid.OptionalString("foregroundColor", func(foreground string) {
		valid.Expect(strings.HasPrefix(foreground, "#"),
			"Invalid foreground color format").
			WithField("foregroundColor").
			And((func() bool {
				n, err := hex.Decode(fgb[:], []byte(foreground[1:]))
				return err == nil && n == 3
			})(), "Invalid foreground color").
			WithField("foregroundColor")
	})
	valid.OptionalString("backgroundColor", func(background string) {
		valid.Expect(strings.HasPrefix(background, "#"),
			"Invalid background color format").
			WithField("backgroundColor").
			And((func() bool {
				n, err := hex.Decode(bgb[:], []byte(background[1:]))
				return err == nil && n == 3
			})(), "Invalid background color").
			WithField("backgroundColor")
	})
	valid.OptionalString("name", func(name string) {
		valid.Expect(len(name) != 0, "Name cannot be empty").WithField(name)
	})
	if !valid.Ok() {
		return nil, nil
	}

	label, err := loaders.ForContext(ctx).LabelsByID.Load(id)
	if err != nil || label == nil {
		return nil, err
	}
	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(label.TrackerID)
	if err != nil {
		return nil, err
	}
	if tracker.OwnerID != auth.ForContext(ctx).UserID {
		return nil, fmt.Errorf("Access denied")
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		var err error
		if len(input) != 0 {
			_, err = database.Apply(label, input).
				Where(database.WithAlias(label.Alias(), `id`)+"= ?", id).
				RunWith(tx).
				ExecContext(ctx)
		}
		return err
	}); err != nil {
		return nil, err
	}
	return label, nil
}

func (r *mutationResolver) DeleteLabel(ctx context.Context, id int) (*model.Label, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *mutationResolver) SubmitTicket(ctx context.Context, trackerID int, input model.SubmitTicketInput) (*model.Ticket, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *mutationResolver) UpdateTicket(ctx context.Context, trackerID int, input map[string]interface{}) (*model.Event, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *mutationResolver) AssignUser(ctx context.Context, ticketID int, userID int) (*model.Event, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *mutationResolver) UnassignUser(ctx context.Context, ticketID int, userID int) (*model.Event, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *mutationResolver) LabelTicket(ctx context.Context, ticketID int, labelID int) (*model.Event, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *mutationResolver) UnlabelTicket(ctx context.Context, ticketID int, labelID int) (*model.Event, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *mutationResolver) SubmitComment(ctx context.Context, ticketID int, text string) (*model.Event, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *queryResolver) Version(ctx context.Context) (*model.Version, error) {
	return &model.Version{
		Major:           0,
		Minor:           0,
		Patch:           0,
		DeprecationDate: nil,
	}, nil
}

func (r *queryResolver) Me(ctx context.Context) (*model.User, error) {
	user := auth.ForContext(ctx)
	return &model.User{
		ID:       user.UserID,
		Created:  user.Created,
		Updated:  user.Updated,
		Username: user.Username,
		Email:    user.Email,
		URL:      user.URL,
		Location: user.Location,
		Bio:      user.Bio,
	}, nil
}

func (r *queryResolver) User(ctx context.Context, username string) (*model.User, error) {
	return loaders.ForContext(ctx).UsersByName.Load(username)
}

func (r *queryResolver) Trackers(ctx context.Context, cursor *coremodel.Cursor) (*model.TrackerCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var trackers []*model.Tracker
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		tracker := (&model.Tracker{}).As(`tr`)
		query := database.
			Select(ctx, tracker).
			From(`tracker tr`).
			Where(`tr.owner_id = ?`, auth.ForContext(ctx).UserID)
		trackers, cursor = tracker.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.TrackerCursor{trackers, cursor}, nil
}

func (r *queryResolver) Tracker(ctx context.Context, id int) (*model.Tracker, error) {
	return loaders.ForContext(ctx).TrackersByID.Load(id)
}

func (r *queryResolver) TrackerByName(ctx context.Context, name string) (*model.Tracker, error) {
	return loaders.ForContext(ctx).TrackersByName.Load(name)
}

func (r *queryResolver) TrackerByOwner(ctx context.Context, owner string, tracker string) (*model.Tracker, error) {
	if strings.HasPrefix(owner, "~") {
		owner = owner[1:]
	} else {
		return nil, fmt.Errorf("Expected owner to be a canonical name")
	}
	return loaders.ForContext(ctx).TrackersByOwnerName.Load([2]string{owner, tracker})
}

func (r *queryResolver) Events(ctx context.Context, cursor *coremodel.Cursor) (*model.EventCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var events []*model.Event
	if err := database.WithTx(ctx, &sql.TxOptions{}, func(tx *sql.Tx) error {
		event := (&model.Event{}).As(`ev`)
		query := database.
			Select(ctx, event).
			From(`event ev`).
			Join(`participant p ON p.user_id = ev.participant_id`).
			Where(`p.user_id = ?`, auth.ForContext(ctx).UserID)
		events, cursor = event.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.EventCursor{events, cursor}, nil
}

func (r *queryResolver) Subscriptions(ctx context.Context, cursor *coremodel.Cursor) (*model.SubscriptionCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var subs []model.Subscription
	if err := database.WithTx(ctx, &sql.TxOptions{}, func(tx *sql.Tx) error {
		sub := (&model.SubscriptionInfo{}).As(`sub`)
		query := database.
			Select(ctx, sub).
			From(`ticket_subscription sub`).
			Join(`participant p ON p.id = sub.participant_id`).
			Where(`p.user_id = ?`, auth.ForContext(ctx).UserID)
		subs, cursor = sub.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.SubscriptionCursor{subs, cursor}, nil
}

func (r *statusChangeResolver) Ticket(ctx context.Context, obj *model.StatusChange) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *statusChangeResolver) Editor(ctx context.Context, obj *model.StatusChange) (model.Entity, error) {
	return loaders.ForContext(ctx).ParticipantsByID.Load(obj.ParticipantID)
}

func (r *ticketResolver) Submitter(ctx context.Context, obj *model.Ticket) (model.Entity, error) {
	return loaders.ForContext(ctx).ParticipantsByID.Load(obj.SubmitterID)
}

func (r *ticketResolver) Tracker(ctx context.Context, obj *model.Ticket) (*model.Tracker, error) {
	return loaders.ForContext(ctx).TrackersByID.Load(obj.TrackerID)
}

func (r *ticketResolver) Labels(ctx context.Context, obj *model.Ticket) ([]*model.Label, error) {
	var labels []*model.Label
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		var (
			err  error
			rows *sql.Rows
		)
		label := (&model.Label{}).As(`l`)
		query := database.
			Select(ctx, label).
			From(`label l`).
			Join(`ticket_label tl ON tl.label_id = l.id`).
			Where(`tl.ticket_id = ?`, obj.PKID)
		if rows, err = query.RunWith(tx).QueryContext(ctx); err != nil {
			panic(err)
		}
		defer rows.Close()

		for rows.Next() {
			var label model.Label
			if err := rows.Scan(database.Scan(ctx, &label)...); err != nil {
				panic(err)
			}
			labels = append(labels, &label)
		}
		return nil
	}); err != nil {
		return nil, err
	}

	return labels, nil
}

func (r *ticketResolver) Assignees(ctx context.Context, obj *model.Ticket) ([]model.Entity, error) {
	var entities []model.Entity
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		var (
			err  error
			rows *sql.Rows
		)
		user := (&model.User{}).As(`u`)
		query := database.
			Select(ctx, user).
			From(`ticket_assignee ta`).
			Join(`"user" u ON ta.assignee_id = u.id`).
			Where(`ta.ticket_id = ?`, obj.PKID)
		if rows, err = query.RunWith(tx).QueryContext(ctx); err != nil {
			panic(err)
		}
		defer rows.Close()

		for rows.Next() {
			var user model.User
			if err := rows.Scan(database.Scan(ctx, &user)...); err != nil {
				panic(err)
			}
			entities = append(entities, &user)
		}
		return nil
	}); err != nil {
		return nil, err
	}

	return entities, nil
}

func (r *ticketResolver) Events(ctx context.Context, obj *model.Ticket, cursor *coremodel.Cursor) (*model.EventCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var events []*model.Event
	if err := database.WithTx(ctx, &sql.TxOptions{}, func(tx *sql.Tx) error {
		event := (&model.Event{}).As(`ev`)
		query := database.
			Select(ctx, event).
			From(`event ev`).
			Where(`ev.ticket_id = ?`, obj.PKID)
		events, cursor = event.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.EventCursor{events, cursor}, nil
}

func (r *ticketResolver) Subscription(ctx context.Context, obj *model.Ticket) (*model.TicketSubscription, error) {
	// Regarding unsafe: if they have access to this ticket resource, they were
	// already authenticated for it.
	return loaders.ForContext(ctx).SubsByTicketIDUnsafe.Load(obj.PKID)
}

func (r *ticketMentionResolver) Ticket(ctx context.Context, obj *model.TicketMention) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *ticketMentionResolver) Author(ctx context.Context, obj *model.TicketMention) (model.Entity, error) {
	return loaders.ForContext(ctx).ParticipantsByID.Load(obj.ParticipantID)
}

func (r *ticketMentionResolver) Mentioned(ctx context.Context, obj *model.TicketMention) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.MentionedID)
}

func (r *ticketSubscriptionResolver) Ticket(ctx context.Context, obj *model.TicketSubscription) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *trackerResolver) Owner(ctx context.Context, obj *model.Tracker) (model.Entity, error) {
	return loaders.ForContext(ctx).UsersByID.Load(obj.OwnerID)
}

func (r *trackerResolver) Tickets(ctx context.Context, obj *model.Tracker, cursor *coremodel.Cursor) (*model.TicketCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var tickets []*model.Ticket
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		ticket := (&model.Ticket{}).As(`tk`)
		var query sq.SelectBuilder
		if obj.CanBrowse() {
			query = database.
				Select(ctx, ticket).
				From(`ticket tk`).
				Where(`tk.tracker_id = ?`, obj.ID)
		} else {
			user := auth.ForContext(ctx)
			query = database.
				Select(ctx, ticket).
				From(`ticket tk`).
				Join(`participant p ON p.user_id = ?`, user.UserID).
				Where(sq.And{
					sq.Expr(`tk.tracker_id = ?`, obj.ID),
					sq.Expr(`tk.submitter_id = p.id`),
				})
		}
		tickets, cursor = ticket.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.TicketCursor{tickets, cursor}, nil
}

func (r *trackerResolver) Labels(ctx context.Context, obj *model.Tracker, cursor *coremodel.Cursor) (*model.LabelCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var labels []*model.Label
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		label := (&model.Label{}).As(`l`)
		query := database.
			Select(ctx, label).
			From(`label l`).
			Where(`l.tracker_id = ?`, obj.ID)
		labels, cursor = label.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.LabelCursor{labels, cursor}, nil
}

func (r *trackerResolver) Subscription(ctx context.Context, obj *model.Tracker) (*model.TrackerSubscription, error) {
	// Regarding unsafe: if they have access to this tracker resource, they
	// were already authenticated for it.
	return loaders.ForContext(ctx).SubsByTrackerIDUnsafe.Load(obj.ID)
}

func (r *trackerResolver) ACL(ctx context.Context, obj *model.Tracker) (model.ACL, error) {
	if obj.ACLID == nil {
		return &model.DefaultACL{
			Browse:  obj.CanBrowse(),
			Submit:  obj.CanSubmit(),
			Comment: obj.CanComment(),
			Edit:    obj.CanEdit(),
			Triage:  obj.CanTriage(),
		}, nil
	}

	acl := (&model.TrackerACL{}).As(`ua`)
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		var access int
		query := database.
			Select(ctx, acl).
			Column(`ua.permissions`).
			From(`user_access ua`).
			Where(`ua.id = ?`, *obj.ACLID)
		row := query.RunWith(tx).QueryRowContext(ctx)
		if err := row.Scan(append(database.Scan(ctx, acl),
			&access)...); err != nil {
			return err
		}
		acl.Browse = access&model.ACCESS_BROWSE != 0
		acl.Submit = access&model.ACCESS_SUBMIT != 0
		acl.Comment = access&model.ACCESS_COMMENT != 0
		acl.Edit = access&model.ACCESS_EDIT != 0
		acl.Triage = access&model.ACCESS_TRIAGE != 0
		return nil
	}); err != nil {
		return nil, err
	}

	return acl, nil
}

func (r *trackerResolver) Acls(ctx context.Context, obj *model.Tracker, cursor *coremodel.Cursor) (*model.ACLCursor, error) {
	if obj.OwnerID != auth.ForContext(ctx).UserID {
		return nil, errors.New("Access denied")
	}

	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var acls []*model.TrackerACL
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		acl := (&model.TrackerACL{}).As(`ua`)
		query := database.
			Select(ctx, acl).
			From(`user_access ua`).
			Where(`ua.tracker_id = ?`, obj.ID)
		acls, cursor = acl.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.ACLCursor{acls, cursor}, nil
}

func (r *trackerResolver) Export(ctx context.Context, obj *model.Tracker) (string, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *trackerACLResolver) Tracker(ctx context.Context, obj *model.TrackerACL) (*model.Tracker, error) {
	return loaders.ForContext(ctx).TrackersByID.Load(obj.TrackerID)
}

func (r *trackerACLResolver) Entity(ctx context.Context, obj *model.TrackerACL) (model.Entity, error) {
	return loaders.ForContext(ctx).UsersByID.Load(obj.UserID)
}

func (r *trackerSubscriptionResolver) Tracker(ctx context.Context, obj *model.TrackerSubscription) (*model.Tracker, error) {
	return loaders.ForContext(ctx).TrackersByID.Load(obj.TrackerID)
}

func (r *userResolver) Trackers(ctx context.Context, obj *model.User, cursor *coremodel.Cursor) (*model.TrackerCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var trackers []*model.Tracker
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		tracker := (&model.Tracker{}).As(`tr`)
		auser := auth.ForContext(ctx)
		query := database.
			Select(ctx, tracker).
			From(`tracker tr`).
			LeftJoin(`user_access ua ON ua.tracker_id = tr.id`).
			Where(sq.And{
				sq.Expr(`tr.owner_id = ?`, obj.ID),
				sq.Or{
					sq.Expr(`tr.owner_id = ?`, auser.UserID),
					sq.Expr(`tr.visibility = 'PUBLIC'`),
					sq.And{
						sq.Expr(`ua.user_id = ?`, auser.UserID),
						sq.Expr(`ua.permissions > 0`),
					},
				},
			})
		trackers, cursor = tracker.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.TrackerCursor{trackers, cursor}, nil
}

func (r *userMentionResolver) Ticket(ctx context.Context, obj *model.UserMention) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *userMentionResolver) Author(ctx context.Context, obj *model.UserMention) (model.Entity, error) {
	return loaders.ForContext(ctx).ParticipantsByID.Load(obj.ParticipantID)
}

func (r *userMentionResolver) Mentioned(ctx context.Context, obj *model.UserMention) (model.Entity, error) {
	return loaders.ForContext(ctx).ParticipantsByID.Load(obj.MentionedID)
}

// Assignment returns api.AssignmentResolver implementation.
func (r *Resolver) Assignment() api.AssignmentResolver { return &assignmentResolver{r} }

// Comment returns api.CommentResolver implementation.
func (r *Resolver) Comment() api.CommentResolver { return &commentResolver{r} }

// Created returns api.CreatedResolver implementation.
func (r *Resolver) Created() api.CreatedResolver { return &createdResolver{r} }

// Event returns api.EventResolver implementation.
func (r *Resolver) Event() api.EventResolver { return &eventResolver{r} }

// Label returns api.LabelResolver implementation.
func (r *Resolver) Label() api.LabelResolver { return &labelResolver{r} }

// LabelUpdate returns api.LabelUpdateResolver implementation.
func (r *Resolver) LabelUpdate() api.LabelUpdateResolver { return &labelUpdateResolver{r} }

// Mutation returns api.MutationResolver implementation.
func (r *Resolver) Mutation() api.MutationResolver { return &mutationResolver{r} }

// Query returns api.QueryResolver implementation.
func (r *Resolver) Query() api.QueryResolver { return &queryResolver{r} }

// StatusChange returns api.StatusChangeResolver implementation.
func (r *Resolver) StatusChange() api.StatusChangeResolver { return &statusChangeResolver{r} }

// Ticket returns api.TicketResolver implementation.
func (r *Resolver) Ticket() api.TicketResolver { return &ticketResolver{r} }

// TicketMention returns api.TicketMentionResolver implementation.
func (r *Resolver) TicketMention() api.TicketMentionResolver { return &ticketMentionResolver{r} }

// TicketSubscription returns api.TicketSubscriptionResolver implementation.
func (r *Resolver) TicketSubscription() api.TicketSubscriptionResolver {
	return &ticketSubscriptionResolver{r}
}

// Tracker returns api.TrackerResolver implementation.
func (r *Resolver) Tracker() api.TrackerResolver { return &trackerResolver{r} }

// TrackerACL returns api.TrackerACLResolver implementation.
func (r *Resolver) TrackerACL() api.TrackerACLResolver { return &trackerACLResolver{r} }

// TrackerSubscription returns api.TrackerSubscriptionResolver implementation.
func (r *Resolver) TrackerSubscription() api.TrackerSubscriptionResolver {
	return &trackerSubscriptionResolver{r}
}

// User returns api.UserResolver implementation.
func (r *Resolver) User() api.UserResolver { return &userResolver{r} }

// UserMention returns api.UserMentionResolver implementation.
func (r *Resolver) UserMention() api.UserMentionResolver { return &userMentionResolver{r} }

type assignmentResolver struct{ *Resolver }
type commentResolver struct{ *Resolver }
type createdResolver struct{ *Resolver }
type eventResolver struct{ *Resolver }
type labelResolver struct{ *Resolver }
type labelUpdateResolver struct{ *Resolver }
type mutationResolver struct{ *Resolver }
type queryResolver struct{ *Resolver }
type statusChangeResolver struct{ *Resolver }
type ticketResolver struct{ *Resolver }
type ticketMentionResolver struct{ *Resolver }
type ticketSubscriptionResolver struct{ *Resolver }
type trackerResolver struct{ *Resolver }
type trackerACLResolver struct{ *Resolver }
type trackerSubscriptionResolver struct{ *Resolver }
type userResolver struct{ *Resolver }
type userMentionResolver struct{ *Resolver }
