package graph

// This file will be automatically regenerated based on the schema, any resolver implementations
// will be copied through when generating and any unknown code will be moved to the end.

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"strings"
	"time"

	"git.sr.ht/~sircmpwn/core-go/auth"
	"git.sr.ht/~sircmpwn/core-go/config"
	"git.sr.ht/~sircmpwn/core-go/database"
	coremodel "git.sr.ht/~sircmpwn/core-go/model"
	"git.sr.ht/~sircmpwn/core-go/server"
	"git.sr.ht/~sircmpwn/core-go/valid"
	corewebhooks "git.sr.ht/~sircmpwn/core-go/webhooks"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/api"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/loaders"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/webhooks"
	"github.com/99designs/gqlgen/graphql"
	sq "github.com/Masterminds/squirrel"
	"github.com/lib/pq"
)

func (r *assignmentResolver) Ticket(ctx context.Context, obj *model.Assignment) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *assignmentResolver) Assigner(ctx context.Context, obj *model.Assignment) (model.Entity, error) {
	return loaders.ForContext(ctx).EntitiesByParticipantID.Load(obj.AssignerID)
}

func (r *assignmentResolver) Assignee(ctx context.Context, obj *model.Assignment) (model.Entity, error) {
	return loaders.ForContext(ctx).EntitiesByParticipantID.Load(obj.AssigneeID)
}

func (r *commentResolver) Ticket(ctx context.Context, obj *model.Comment) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *commentResolver) Author(ctx context.Context, obj *model.Comment) (model.Entity, error) {
	return loaders.ForContext(ctx).EntitiesByParticipantID.Load(obj.ParticipantID)
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
	return loaders.ForContext(ctx).EntitiesByParticipantID.Load(obj.ParticipantID)
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
	return loaders.ForContext(ctx).EntitiesByParticipantID.Load(obj.ParticipantID)
}

func (r *labelUpdateResolver) Label(ctx context.Context, obj *model.LabelUpdate) (*model.Label, error) {
	return loaders.ForContext(ctx).LabelsByID.Load(obj.LabelID)
}

func (r *mutationResolver) CreateTracker(ctx context.Context, name string, description *string, visibility model.Visibility, importArg *graphql.Upload) (*model.Tracker, error) {
	validation := valid.New(ctx)
	validation.Expect(trackerNameRE.MatchString(name), "Name must match %s", trackerNameRE.String()).
		WithField("name").
		And(name != "." && name != ".." && name != ".git" && name != ".hg",
			"This is a reserved name and cannot be used for user trakcers.").
		WithField("name")
	// TODO: Unify description limits
	validation.Expect(description == nil || len(*description) < 8192,
		"Description must be fewer than 8192 characters").
		WithField("description")
	validation.Expect(importArg == nil, "TODO: imports").WithField("import") // TODO
	if !validation.Ok() {
		return nil, nil
	}

	user := auth.ForContext(ctx)
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	var tracker model.Tracker
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			INSERT INTO tracker (
				created, updated,
				owner_id, name, description, visibility
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				$1, $2, $3, $4
			)
			RETURNING id, owner_id, created, updated, name, description,
				visibility, default_access;
		`, user.UserID, name, description, visibility.String())

		if err := row.Scan(&tracker.ID, &tracker.OwnerID, &tracker.Created,
			&tracker.Updated, &tracker.Name, &tracker.Description,
			&tracker.Visibility, &tracker.DefaultAccess); err != nil {
			if err, ok := err.(*pq.Error); ok &&
				err.Code == "23505" && // unique_violation
				err.Constraint == "tracker_owner_id_name_unique" {
				return valid.Error(ctx, "name",
					"A tracker by this name already exists.")
			}
			return err
		}
		tracker.Access = model.ACCESS_ALL

		_, err := tx.ExecContext(ctx, `
			INSERT INTO ticket_subscription (
				created, updated, tracker_id, participant_id
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				$1, $2
			);
		`, tracker.ID, part.ID)
		return err
	}); err != nil {
		return nil, err
	}
	webhooks.DeliverLegacyTrackerEvent(ctx, &tracker, "tracker:create")
	webhooks.DeliverTrackerEvent(ctx, model.WebhookEventTrackerCreated, &tracker)
	return &tracker, nil
}

func (r *mutationResolver) UpdateTracker(ctx context.Context, id int, input map[string]interface{}) (*model.Tracker, error) {
	query := sq.Update("tracker").
		PlaceholderFormat(sq.Dollar)

	validation := valid.New(ctx).WithInput(input)

	validation.OptionalString("description", func(desc string) {
		validation.Expect(len(desc) < 8192,
			"Description must be fewer than 8192 characters").
			WithField("description")
		if !validation.Ok() {
			return
		}
		query = query.Set(`description`, desc)
	})
	validation.OptionalString("visibility", func(vis string) {
		query = query.Set(`visibility`, vis)
	})
	if !validation.Ok() {
		return nil, nil
	}

	var tracker model.Tracker
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		query = query.
			Where(`id = ?`, id).
			Where(`owner_id = ?`, auth.ForContext(ctx).UserID).
			Set(`updated`, sq.Expr(`now() at time zone 'utc'`)).
			Suffix(`RETURNING
					id, created, updated, name, description, visibility,
					default_access, owner_id`)

		row := query.RunWith(tx).QueryRowContext(ctx)
		if err := row.Scan(&tracker.ID, &tracker.Created, &tracker.Updated,
			&tracker.Name, &tracker.Description, &tracker.Visibility,
			&tracker.DefaultAccess, &tracker.OwnerID); err != nil {
			if err == sql.ErrNoRows {
				return fmt.Errorf("No tracker by ID %d found for this user", id)
			}
			return err
		}
		return nil
	}); err != nil {
		return nil, err
	}
	webhooks.DeliverLegacyTrackerEvent(ctx, &tracker, "tracker:update")
	webhooks.DeliverTrackerEvent(ctx, model.WebhookEventTrackerUpdate, &tracker)
	return &tracker, nil
}

func (r *mutationResolver) DeleteTracker(ctx context.Context, id int) (*model.Tracker, error) {
	user := auth.ForContext(ctx)

	var tracker model.Tracker
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			DELETE FROM tracker
			WHERE id = $1 AND owner_id = $2
			RETURNING
				id, owner_id, created, updated, name, description, visibility,
				default_access;
		`, id, user.UserID)

		if err := row.Scan(&tracker.ID, &tracker.OwnerID, &tracker.Created,
			&tracker.Updated, &tracker.Name, &tracker.Description,
			&tracker.Visibility, &tracker.DefaultAccess); err != nil {
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

	webhooks.DeliverLegacyTrackerDelete(ctx, tracker.ID, user.UserID)
	webhooks.DeliverTrackerEvent(ctx, model.WebhookEventTrackerDeleted, &tracker)
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

		acl.SetBits(bits)
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
	var tracker model.Tracker // Need to load tracker data for webhook delivery
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			UPDATE tracker
			SET default_access = $1
			WHERE id = $2 AND owner_id = $3
			RETURNING
				id, created, updated, name, description, visibility,
				default_access, owner_id;
		`, bits, trackerID, user.UserID)
		if err := row.Scan(&tracker.ID, &tracker.Created, &tracker.Updated,
			&tracker.Name, &tracker.Description, &tracker.Visibility,
			&tracker.DefaultAccess, &tracker.OwnerID); err != nil {
			return err
		}
		return nil
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	webhooks.DeliverLegacyTrackerEvent(ctx, &tracker, "tracker:update")
	webhooks.DeliverTrackerEvent(ctx, model.WebhookEventTrackerUpdate, &tracker)
	acl := &model.DefaultACL{}
	acl.SetBits(bits)
	return acl, nil
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

		acl.SetBits(bits)
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
	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(trackerID)
	if err != nil {
		return nil, err
	} else if tracker == nil {
		return nil, fmt.Errorf("Access denied")
	}
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			INSERT INTO ticket_subscription (
				created, updated, tracker_id, participant_id
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				$1, $2
			)
			ON CONFLICT ON CONSTRAINT subscription_tracker_participant_uq
			DO UPDATE SET updated = NOW() at time zone 'utc'
			RETURNING id, created, tracker_id;
		`, tracker.ID, part.ID)
		return row.Scan(&sub.ID, &sub.Created, &sub.TrackerID)
	}); err != nil {
		return nil, err
	}
	return &sub, nil
}

func (r *mutationResolver) TrackerUnsubscribe(ctx context.Context, trackerID int, tickets bool) (*model.TrackerSubscription, error) {
	var sub model.TrackerSubscription

	user := auth.ForContext(ctx)
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	if tickets {
		panic("not implemented") // TODO
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			DELETE FROM ticket_subscription
			WHERE tracker_id = $1 AND participant_id = $2
			RETURNING id, created, tracker_id;
		`, trackerID, part.ID)
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
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	ticket, err := loaders.ForContext(ctx).
		TicketsByTrackerID.Load([2]int{trackerID, ticketID})
	if err != nil {
		return nil, err
	} else if ticket == nil {
		return nil, nil
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			INSERT INTO ticket_subscription (
				created, updated, ticket_id, participant_id
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				$1, $2
			)
			ON CONFLICT ON CONSTRAINT subscription_ticket_participant_uq
			DO UPDATE SET updated = NOW() at time zone 'utc'
			RETURNING id, created, ticket_id;
		`, ticket.PKID, part.ID)
		return row.Scan(&sub.ID, &sub.Created, &sub.TicketID)
	}); err != nil {
		return nil, err
	}
	return &sub, nil
}

func (r *mutationResolver) TicketUnsubscribe(ctx context.Context, trackerID int, ticketID int) (*model.TicketSubscription, error) {
	var sub model.TicketSubscription

	user := auth.ForContext(ctx)
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	ticket, err := loaders.ForContext(ctx).
		TicketsByTrackerID.Load([2]int{trackerID, ticketID})
	if err != nil {
		return nil, err
	} else if ticket == nil {
		return nil, nil
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			DELETE FROM ticket_subscription
			WHERE ticket_id = $1 AND participant_id = $2
			RETURNING id, created, ticket_id;
		`, ticket.PKID, part.ID)
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
	var (
		err   error
		label model.Label
	)
	user := auth.ForContext(ctx)
	if _, err = parseColor(foreground); err != nil {
		return nil, err
	}
	if _, err = parseColor(background); err != nil {
		return nil, err
	}
	if len(name) <= 0 {
		return nil, fmt.Errorf("Label name must be greater than zero in length")
	}
	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(trackerID)
	if err != nil {
		return nil, err
	} else if tracker == nil {
		return nil, nil
	}
	if tracker.OwnerID != user.UserID {
		return nil, fmt.Errorf("Access denied")
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		// TODO: Rename the columns for consistency
		row := tx.QueryRowContext(ctx, `
			INSERT INTO label (
				created, updated, tracker_id, name, color, text_color
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				$1, $2, $3, $4
			) RETURNING id, created, name, color, text_color, tracker_id;
		`, tracker.ID, name, background, foreground)

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
	webhooks.DeliverLegacyLabelCreate(ctx, tracker, &label)
	return &label, nil
}

func (r *mutationResolver) UpdateLabel(ctx context.Context, id int, input map[string]interface{}) (*model.Label, error) {
	query := sq.Update("label").
		PlaceholderFormat(sq.Dollar)

	validation := valid.New(ctx).WithInput(input)
	validation.OptionalString("foregroundColor", func(foreground string) {
		_, err := parseColor(foreground)
		if err != nil {
			validation.Error("%s", err.Error()).WithField("foregroundColor")
			return
		}
		query = query.Set(`text_color`, foreground)
	})
	validation.OptionalString("backgroundColor", func(background string) {
		_, err := parseColor(background)
		if err != nil {
			validation.Error("%s", err.Error()).WithField("backgroundColor")
			return
		}
		query = query.Set(`color`, background)
	})
	validation.OptionalString("name", func(name string) {
		validation.Expect(len(name) != 0, "Name cannot be empty").
			WithField("name")
		if !validation.Ok() {
			return
		}
		query = query.Set(`name`, name)
	})
	if !validation.Ok() {
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
			_, err = query.
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
	var label model.Label
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			DELETE FROM label
			USING tracker
			WHERE
				label.tracker_id = tracker.id AND
				tracker.owner_id = $1 AND
				label.id = $2
			 RETURNING label.id, label.created, label.name, label.color,
				 label.text_color, label.tracker_id;
		`, auth.ForContext(ctx).UserID, id)
		return row.Scan(&label.ID, &label.Created, &label.Name,
			&label.BackgroundColor, &label.ForegroundColor, &label.TrackerID)
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	webhooks.DeliverLegacyLabelDelete(ctx, label.TrackerID, label.ID)
	return &label, nil
}

func (r *mutationResolver) SubmitTicket(ctx context.Context, trackerID int, input model.SubmitTicketInput) (*model.Ticket, error) {
	validation := valid.New(ctx)
	validation.Expect(len(input.Subject) <= 2048,
		"Ticket subject must be fewer than to 2049 characters.").
		WithField("subject")
	if input.Body != nil {
		validation.Expect(len(*input.Body) <= 16384,
			"Ticket body must be less than 16 KiB in size").
			WithField("body")
	}
	validation.Expect((input.ExternalID == nil) == (input.ExternalURL == nil),
		"Must specify both externalId and externalUrl, or neither, but not one")
	if !validation.Ok() {
		return nil, nil
	}

	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(trackerID)
	if err != nil || tracker == nil {
		return nil, err
	}

	owner, err := loaders.ForContext(ctx).UsersByID.Load(tracker.OwnerID)
	if err != nil {
		panic(err)
	}

	if !tracker.CanSubmit() {
		return nil, fmt.Errorf("Access denied")
	}

	user := auth.ForContext(ctx)
	if input.ExternalID != nil {
		validation.Expect(tracker.OwnerID == user.UserID,
			"Cannot configure external user import unless you are the owner of this tracker")
		validation.Expect(strings.ContainsRune(*input.ExternalID, ':'),
			"Format of externalId field is '<third-party>:<name>', .e.g 'example.org:jdoe'").
			WithField("externalId")
		u, err := url.Parse(*input.ExternalURL)
		if err != nil {
			return nil, valid.Error(ctx, "externalUrl", err.Error())
		}
		if u.Scheme != "http" && u.Scheme != "https" {
			return nil, valid.Error(ctx, "externalUrl", "Invalid URL scheme")
		}
	}
	if input.Created != nil {
		validation.Expect(tracker.OwnerID == user.UserID,
			"Cannot configure creation time unless you are the owner of this tracker").
			WithField("created")
		var zeroDate time.Time
		validation.Expect(*input.Created != zeroDate,
			"Cannot use zero value for creation time").
			WithField("created")
	}
	if !validation.Ok() {
		return nil, nil
	}

	var ticket model.Ticket
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		var participant *model.Participant
		if input.ExternalID != nil {
			row := tx.QueryRowContext(ctx, `
				INSERT INTO participant (
					created, participant_type, external_id, external_url
				) VALUES (
					NOW() at time zone 'utc',
					'external', $1, $2
				)
				ON CONFLICT ON CONSTRAINT participant_external_id_key
				DO UPDATE SET created = participant.created
				RETURNING id
			`, *input.ExternalID, *input.ExternalURL)
			participant = &model.Participant{}
			if err := row.Scan(&participant.ID); err != nil {
				return err
			}
		} else {
			var err error
			participant, err = loaders.ForContext(ctx).
				ParticipantsByUserID.Load(user.UserID)
			if err != nil {
				panic(err)
			}
		}

		row := tx.QueryRowContext(ctx, `
			WITH tr AS (
				UPDATE tracker
				SET
					next_ticket_id = next_ticket_id + 1,
					updated = NOW() at time zone 'utc'
				WHERE id = $1
				RETURNING id, next_ticket_id, name
			) INSERT INTO ticket (
				created, updated,
				tracker_id, scoped_id,
				submitter_id, title, description
			) VALUES (
				COALESCE($2, NOW() at time zone 'utc'),
				NOW() at time zone 'utc',
				(SELECT id FROM tr),
				(SELECT next_ticket_id - 1 FROM tr),
				$3, $4, $5
			)
			RETURNING
				id, scoped_id, submitter_id, tracker_id, created, updated,
				title, description, authenticity, status, resolution;`,
			trackerID, input.Created, participant.ID, input.Subject, input.Body)
		if err := row.Scan(&ticket.PKID, &ticket.ID, &ticket.SubmitterID,
			&ticket.TrackerID, &ticket.Created, &ticket.Updated, &ticket.Subject,
			&ticket.Body, &ticket.RawAuthenticity, &ticket.RawStatus,
			&ticket.RawResolution); err != nil {
			return err
		}

		ticket.OwnerName = owner.Username
		ticket.TrackerName = tracker.Name

		conf := config.ForContext(ctx)
		origin := config.GetOrigin(conf, "todo.sr.ht", true)

		builder := NewEventBuilder(ctx, tx, participant.ID, model.EVENT_CREATED).
			WithTicket(tracker, &ticket)

		if ticket.Body != nil {
			mentions := ScanMentions(ctx, tracker, &ticket, *ticket.Body)
			builder.AddMentions(&mentions)
		}

		builder.InsertSubscriptions()

		var eventID int
		row = tx.QueryRowContext(ctx, `
			INSERT INTO event (
				created, event_type, participant_id, ticket_id
			) VALUES (
				NOW() at time zone 'utc',
				$1, $2, $3
			) RETURNING id;
		`, model.EVENT_CREATED, participant.ID, ticket.PKID)
		if err := row.Scan(&eventID); err != nil {
			panic(err)
		}

		builder.InsertNotifications(eventID, nil)

		details := NewTicketDetails{
			Body: ticket.Body,
			Root: origin,
			TicketURL: fmt.Sprintf("/%s/%s/%d",
				owner.CanonicalName(), tracker.Name, ticket.ID),
		}
		subject := fmt.Sprintf("%s: %s", ticket.Ref(), ticket.Subject)
		builder.SendEmails(subject, newTicketTemplate, &details)
		return nil
	}); err != nil {
		return nil, err
	}
	webhooks.DeliverLegacyTicketCreate(ctx, tracker, &ticket)
	webhooks.DeliverTicketEvent(ctx, model.WebhookEventTicketCreated, &ticket)
	return &ticket, nil
}

func (r *mutationResolver) UpdateTicket(ctx context.Context, trackerID int, ticketID int, input map[string]interface{}) (*model.Ticket, error) {
	if _, ok := input["import"]; ok {
		panic(fmt.Errorf("not implemented")) // TODO
	}

	update := sq.Update("ticket").
		PlaceholderFormat(sq.Dollar)

	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(trackerID)
	if err != nil {
		return nil, err
	} else if tracker == nil {
		return nil, nil
	}
	if !tracker.CanEdit() {
		return nil, fmt.Errorf("Access denied")
	}

	ticket, err := loaders.ForContext(ctx).
		TicketsByTrackerID.Load([2]int{trackerID, ticketID})
	if err != nil {
		return nil, err
	} else if ticket == nil {
		return nil, nil
	}

	validation := valid.New(ctx).WithInput(input)
	// TODO: Rename database columns title => subject; description => body
	validation.OptionalString("subject", func(subject string) {
		validation.Expect(len(subject) < 2049,
			"Ticket subject must be fewer than 2049 characters.").
			WithField("subject")
		if !validation.Ok() {
			return
		}
		ticket.Subject = subject
		update = update.Set("title", subject)
	})
	validation.NullableString("body", func(body *string) {
		if body != nil {
			validation.Expect(len(*body) <= 16384,
				"Ticket body must be less than 16 KiB in size").
				WithField("body")
			if !validation.Ok() {
				return
			}
		}
		ticket.Body = body
		update = update.Set("description", body)
	})
	if !validation.Ok() {
		return nil, nil
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		_, err := update.
			Where(`ticket.id = ?`, ticket.PKID).
			RunWith(tx).
			ExecContext(ctx)
		if err != nil {
			return err
		}
		return nil
	}); err != nil {
		return nil, err
	}

	return ticket, nil
}

func (r *mutationResolver) UpdateTicketStatus(ctx context.Context, trackerID int, ticketID int, input model.UpdateStatusInput) (*model.Event, error) {
	if input.Import != nil {
		panic(fmt.Errorf("not implemented")) // TODO
	}

	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(trackerID)
	if err != nil {
		return nil, err
	} else if tracker == nil {
		return nil, nil
	}
	if !tracker.CanTriage() {
		return nil, fmt.Errorf("Access denied")
	}

	ticket, err := loaders.ForContext(ctx).
		TicketsByTrackerID.Load([2]int{trackerID, ticketID})
	if err != nil {
		return nil, err
	} else if ticket == nil {
		return nil, nil
	}

	owner, err := loaders.ForContext(ctx).UsersByID.Load(tracker.OwnerID)
	if err != nil {
		panic(err)
	}

	user := auth.ForContext(ctx)
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	update := sq.Update("ticket").
		PlaceholderFormat(sq.Dollar).
		Set("status", input.Status.ToInt())
	insert := sq.Insert("event").
		PlaceholderFormat(sq.Dollar).
		Columns("created", "event_type",
			"ticket_id", "participant_id",
			"old_status", "new_status",
			"old_resolution", "new_resolution")

	resolution := ticket.Resolution()
	if input.Resolution != nil {
		resolution = *input.Resolution
		update = update.Set("resolution", resolution.ToInt())
	} else if input.Status.ToInt() == model.STATUS_RESOLVED {
		return nil, fmt.Errorf("resolution is required when status is RESOLVED")
	}

	var event model.Event
	insert = insert.Values(sq.Expr("now() at time zone 'utc'"),
		model.EVENT_STATUS_CHANGE, ticket.PKID, part.ID,
		ticket.Status().ToInt(), input.Status.ToInt(),
		ticket.Resolution().ToInt(), resolution.ToInt())
	columns := database.Columns(ctx, &event)

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		_, err := update.
			Where(`ticket.id = ?`, ticket.PKID).
			RunWith(tx).
			ExecContext(ctx)
		if err != nil {
			return err
		}

		err = insert.
			Suffix(`RETURNING ` + strings.Join(columns, ", ")).
			RunWith(tx).
			QueryRowContext(ctx).
			Scan(database.Scan(ctx, &event)...)
		if err != nil {
			return err
		}

		builder := NewEventBuilder(ctx, tx, part.ID, model.EVENT_STATUS_CHANGE).
			WithTicket(tracker, ticket)
		builder.InsertNotifications(event.ID, nil)

		// Send notification emails
		conf := config.ForContext(ctx)
		origin := config.GetOrigin(conf, "todo.sr.ht", true)
		details := TicketStatusDetails{
			Root: origin,
			TicketURL: fmt.Sprintf("/%s/%s/%d",
				owner.CanonicalName(), tracker.Name, ticket.ID),
			EventID:    event.ID,
			Status:     input.Status.String(),
			Resolution: resolution.String(),
		}
		subject := fmt.Sprintf("Re: %s: %s", ticket.Ref(), ticket.Subject)
		builder.SendEmails(subject, ticketStatusTemplate, &details)
		return nil
	}); err != nil {
		return nil, err
	}
	webhooks.DeliverLegacyEventCreate(ctx, tracker, ticket, &event)
	return &event, nil
}

func (r *mutationResolver) SubmitComment(ctx context.Context, trackerID int, ticketID int, input model.SubmitCommentInput) (*model.Event, error) {
	if input.Import != nil {
		panic(fmt.Errorf("not implemented")) // TODO
	}

	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(trackerID)
	if err != nil {
		return nil, err
	} else if tracker == nil {
		return nil, nil
	}
	if !tracker.CanComment() {
		return nil, fmt.Errorf("Access denied")
	}
	if (input.Status != nil || input.Resolution != nil) && !tracker.CanTriage() {
		return nil, fmt.Errorf("Access denied")
	}

	ticket, err := loaders.ForContext(ctx).
		TicketsByTrackerID.Load([2]int{trackerID, ticketID})
	if err != nil {
		return nil, err
	} else if ticket == nil {
		return nil, nil
	}

	owner, err := loaders.ForContext(ctx).UsersByID.Load(tracker.OwnerID)
	if err != nil {
		panic(err)
	}

	user := auth.ForContext(ctx)
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	updateTicket := sq.Update("ticket").
		PlaceholderFormat(sq.Dollar)
	insertEvent := sq.Insert("event").
		PlaceholderFormat(sq.Dollar).
		Columns("created", "event_type",
			"ticket_id", "participant_id", "comment_id",
			"old_status", "new_status", "old_resolution", "new_resolution")

	var (
		oldStatus      *int
		_oldStatus     int
		newStatus      *int
		_newStatus     int
		oldResolution  *int
		_oldResolution int
		newResolution  *int
		_newResolution int
		eventType      uint = model.EVENT_COMMENT
	)
	if input.Status != nil {
		eventType |= model.EVENT_STATUS_CHANGE
		oldStatus = &_oldStatus
		newStatus = &_newStatus
		oldResolution = &_oldResolution
		newResolution = &_newResolution
		*oldStatus = ticket.Status().ToInt()
		*oldResolution = ticket.Resolution().ToInt()
		*newStatus = input.Status.ToInt()
		*newResolution = ticket.Resolution().ToInt()
		updateTicket = updateTicket.Set("status", *newStatus)
		if input.Resolution != nil {
			*newResolution = input.Resolution.ToInt()
			updateTicket = updateTicket.Set("resolution", *newResolution)
		} else if input.Status.ToInt() == model.STATUS_RESOLVED {
			return nil, fmt.Errorf("resolution is required when status is RESOLVED")
		}
	}

	var event model.Event
	columns := database.Columns(ctx, &event)
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		builder := NewEventBuilder(ctx, tx, part.ID, eventType).
			WithTicket(tracker, ticket)

		mentions := ScanMentions(ctx, tracker, ticket, input.Text)
		builder.AddMentions(&mentions)

		_, err := updateTicket.
			Set(`comment_count`, sq.Expr(`comment_count + 1`)).
			Where(`ticket.id = ?`, ticket.PKID).
			RunWith(tx).
			ExecContext(ctx)
		if err != nil {
			return err
		}

		row := tx.QueryRowContext(ctx, `
			INSERT INTO ticket_comment (
				created, updated, submitter_id, ticket_id, text
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				$1, $2, $3
			) RETURNING id;
		`, part.ID, ticket.PKID, input.Text)

		var commentID int
		if err := row.Scan(&commentID); err != nil {
			return err
		}

		builder.InsertSubscriptions()

		eventRow := insertEvent.Values(sq.Expr("now() at time zone 'utc'"),
			eventType, ticket.PKID, part.ID, commentID,
			oldStatus, newStatus, oldResolution, newResolution).
			Suffix(`RETURNING ` + strings.Join(columns, ", ")).
			RunWith(tx).
			QueryRowContext(ctx)
		if err := eventRow.Scan(database.Scan(ctx, &event)...); err != nil {
			return err
		}
		builder.InsertNotifications(event.ID, &commentID)

		conf := config.ForContext(ctx)
		origin := config.GetOrigin(conf, "todo.sr.ht", true)
		details := SubmitCommentDetails{
			Root: origin,
			TicketURL: fmt.Sprintf("/%s/%s/%d",
				owner.CanonicalName(), tracker.Name, ticket.ID),
			EventID:       event.ID,
			Comment:       input.Text,
			StatusUpdated: input.Status != nil,
		}
		if details.StatusUpdated {
			details.Status = model.TicketStatusFromInt(*newStatus).String()
			details.Resolution = model.TicketResolutionFromInt(*newResolution).String()
		}
		subject := fmt.Sprintf("Re: %s: %s", ticket.Ref(), ticket.Subject)
		builder.SendEmails(subject, submitCommentTemplate, &details)
		return nil
	}); err != nil {
		return nil, err
	}
	webhooks.DeliverLegacyEventCreate(ctx, tracker, ticket, &event)
	return &event, nil
}

func (r *mutationResolver) AssignUser(ctx context.Context, trackerID int, ticketID int, userID int) (*model.Event, error) {
	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(trackerID)
	if err != nil {
		return nil, err
	} else if tracker == nil {
		return nil, nil
	}
	if !tracker.CanTriage() {
		return nil, fmt.Errorf("Access denied")
	}

	owner, err := loaders.ForContext(ctx).UsersByID.Load(tracker.OwnerID)
	if err != nil {
		panic(err)
	}

	ticket, err := loaders.ForContext(ctx).
		TicketsByTrackerID.Load([2]int{trackerID, ticketID})
	if err != nil {
		return nil, err
	} else if ticket == nil {
		return nil, nil
	}

	assignedUser, err := loaders.ForContext(ctx).UsersByID.Load(userID)
	if err != nil {
		return nil, err
	} else if assignedUser == nil {
		return nil, nil
	}

	assignee, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(userID)
	if err != nil {
		return nil, err
	} else if assignee == nil {
		return nil, nil
	}

	user := auth.ForContext(ctx)
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	var event model.Event
	insertEvent := sq.Insert("event").
		PlaceholderFormat(sq.Dollar).
		Columns("created", "event_type", "ticket_id",
			"participant_id", "by_participant_id").
		Values(sq.Expr("now() at time zone 'utc'"),
			model.EVENT_ASSIGNED_USER, ticket.PKID,
			assignee.ID, part.ID)

	columns := database.Columns(ctx, &event)
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `
			INSERT INTO ticket_assignee (
				created, updated, ticket_id,
				assignee_id, assigner_id
			) VALUES (
				NOW() at time zone 'utc',
				NOW() at time zone 'utc',
				$1, $2, $3
			)`, ticket.PKID, userID, user.UserID)
		if err, ok := err.(*pq.Error); ok &&
			err.Code == "23505" && // unique_violation
			err.Constraint == "idx_ticket_assignee_unique" {
			return valid.Error(ctx, "userId",
				"This user is already assigned to this ticket")
		} else if err != nil {
			return err
		}

		_, err = tx.ExecContext(ctx, `
			UPDATE ticket
			SET updated = NOW() at time zone 'utc'
			WHERE id = $1
		`, ticket.PKID)
		if err != nil {
			return nil
		}

		row := insertEvent.
			Suffix(`RETURNING ` + strings.Join(columns, ", ")).
			RunWith(tx).
			QueryRowContext(ctx)
		if err := row.Scan(database.Scan(ctx, &event)...); err != nil {
			return err
		}

		builder := NewEventBuilder(ctx, tx, part.ID, model.EVENT_ASSIGNED_USER).
			WithTicket(tracker, ticket)
		_, err = builder.tx.ExecContext(builder.ctx, `
			INSERT INTO event_participant (
				participant_id, event_type, subscribe
			) VALUES (
				$1, $2, true
			);
		`, assignee.ID, model.EVENT_ASSIGNED_USER)
		if err != nil {
			panic(err)
		}
		builder.InsertSubscriptions()
		builder.InsertNotifications(event.ID, nil)

		conf := config.ForContext(ctx)
		origin := config.GetOrigin(conf, "todo.sr.ht", true)
		details := TicketAssignedDetails{
			Root: origin,
			TicketURL: fmt.Sprintf("/%s/%s/%d",
				owner.CanonicalName(), tracker.Name, ticket.ID),
			EventID:  event.ID,
			Assigned: true,
			Assigner: user.Username,
			Assignee: assignedUser.Username,
		}
		subject := fmt.Sprintf("Re: %s: %s", ticket.Ref(), ticket.Subject)
		builder.SendEmails(subject, ticketAssignedTemplate, &details)
		return nil
	}); err != nil {
		return nil, err
	}
	webhooks.DeliverLegacyEventCreate(ctx, tracker, ticket, &event)
	return &event, nil
}

func (r *mutationResolver) UnassignUser(ctx context.Context, trackerID int, ticketID int, userID int) (*model.Event, error) {
	// XXX: I wonder how much of this can be shared with AssignUser
	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(trackerID)
	if err != nil {
		return nil, err
	} else if tracker == nil {
		return nil, nil
	}
	if !tracker.CanTriage() {
		return nil, fmt.Errorf("Access denied")
	}

	owner, err := loaders.ForContext(ctx).UsersByID.Load(tracker.OwnerID)
	if err != nil {
		panic(err)
	}

	ticket, err := loaders.ForContext(ctx).
		TicketsByTrackerID.Load([2]int{trackerID, ticketID})
	if err != nil {
		return nil, err
	} else if ticket == nil {
		return nil, nil
	}

	assignedUser, err := loaders.ForContext(ctx).UsersByID.Load(userID)
	if err != nil {
		return nil, err
	} else if assignedUser == nil {
		return nil, nil
	}

	assignee, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(userID)
	if err != nil {
		return nil, err
	} else if assignee == nil {
		return nil, nil
	}

	user := auth.ForContext(ctx)
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	var event model.Event
	insertEvent := sq.Insert("event").
		PlaceholderFormat(sq.Dollar).
		Columns("created", "event_type", "ticket_id",
			"participant_id", "by_participant_id").
		Values(sq.Expr("now() at time zone 'utc'"),
			model.EVENT_UNASSIGNED_USER, ticket.PKID,
			assignee.ID, part.ID)

	columns := database.Columns(ctx, &event)
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		var taId int
		err := tx.QueryRowContext(ctx, `
			DELETE FROM ticket_assignee
			WHERE ticket_id = $1 AND assignee_id = $2
			RETURNING id`,
			ticket.PKID, userID).
			Scan(&taId)
		if err == sql.ErrNoRows {
			return valid.Error(ctx, "userId",
				"This user is not assigned to this ticket")
		} else if err != nil {
			return err
		}

		_, err = tx.ExecContext(ctx, `
			UPDATE ticket
			SET updated = NOW() at time zone 'utc'
			WHERE id = $1
		`, ticket.PKID)
		if err != nil {
			return nil
		}

		row := insertEvent.
			Suffix(`RETURNING ` + strings.Join(columns, ", ")).
			RunWith(tx).
			QueryRowContext(ctx)
		if err := row.Scan(database.Scan(ctx, &event)...); err != nil {
			return err
		}

		builder := NewEventBuilder(ctx, tx, part.ID, model.EVENT_UNASSIGNED_USER).
			WithTicket(tracker, ticket)
		_, err = builder.tx.ExecContext(builder.ctx, `
			INSERT INTO event_participant (
				participant_id, event_type, subscribe
			) VALUES (
				$1, $2, true
			);
		`, assignee.ID, model.EVENT_UNASSIGNED_USER)
		if err != nil {
			panic(err)
		}
		builder.InsertSubscriptions()
		builder.InsertNotifications(event.ID, nil)

		conf := config.ForContext(ctx)
		origin := config.GetOrigin(conf, "todo.sr.ht", true)
		details := TicketAssignedDetails{
			Root: origin,
			TicketURL: fmt.Sprintf("/%s/%s/%d",
				owner.CanonicalName(), tracker.Name, ticket.ID),
			EventID:  event.ID,
			Assigned: false,
			Assigner: user.Username,
			Assignee: assignedUser.Username,
		}
		subject := fmt.Sprintf("Re: %s: %s", ticket.Ref(), ticket.Subject)
		builder.SendEmails(subject, ticketAssignedTemplate, &details)
		return nil
	}); err != nil {
		return nil, err
	}
	webhooks.DeliverLegacyEventCreate(ctx, tracker, ticket, &event)
	return &event, nil
}

func (r *mutationResolver) LabelTicket(ctx context.Context, trackerID int, ticketID int, labelID int) (*model.Event, error) {
	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(trackerID)
	if err != nil {
		return nil, err
	} else if tracker == nil {
		return nil, fmt.Errorf("No such tracker")
	}
	if !tracker.CanTriage() {
		return nil, fmt.Errorf("Access denied")
	}

	ticket, err := loaders.ForContext(ctx).
		TicketsByTrackerID.Load([2]int{trackerID, ticketID})
	if err != nil {
		return nil, err
	} else if ticket == nil {
		return nil, fmt.Errorf("No such ticket")
	}

	label, err := loaders.ForContext(ctx).
		LabelsByID.Load(labelID)
	if err != nil {
		return nil, err
	} else if label == nil {
		return nil, fmt.Errorf("No such label")
	}

	user := auth.ForContext(ctx)
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	var event model.Event
	insertEvent := sq.Insert("event").
		PlaceholderFormat(sq.Dollar).
		Columns("created", "event_type", "ticket_id",
			"participant_id", "label_id").
		Values(sq.Expr("now() at time zone 'utc'"),
			model.EVENT_LABEL_ADDED, ticket.PKID, part.ID, label.ID)

	columns := database.Columns(ctx, &event)
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `
			INSERT INTO ticket_label (
				created, ticket_id, label_id, user_id
			) VALUES (
				NOW() at time zone 'utc',
				$1, $2, $3
			)`, ticket.PKID, label.ID, user.UserID)
		if err, ok := err.(*pq.Error); ok &&
			err.Code == "23505" && // unique_violation
			err.Constraint == "ticket_label_pkey" {
			return valid.Error(ctx, "userId",
				"This label is already assigned to this ticket")
		} else if err != nil {
			return err
		}

		_, err = tx.ExecContext(ctx, `
			UPDATE ticket
			SET updated = NOW() at time zone 'utc'
			WHERE id = $1
		`, ticket.PKID)
		if err != nil {
			return nil
		}

		row := insertEvent.
			Suffix(`RETURNING ` + strings.Join(columns, ", ")).
			RunWith(tx).
			QueryRowContext(ctx)
		if err := row.Scan(database.Scan(ctx, &event)...); err != nil {
			return err
		}

		builder := NewEventBuilder(ctx, tx, part.ID, model.EVENT_LABEL_ADDED).
			WithTicket(tracker, ticket)
		builder.InsertNotifications(event.ID, nil)
		return nil
	}); err != nil {
		return nil, err
	}
	webhooks.DeliverLegacyEventCreate(ctx, tracker, ticket, &event)
	return &event, nil
}

func (r *mutationResolver) UnlabelTicket(ctx context.Context, trackerID int, ticketID int, labelID int) (*model.Event, error) {
	// XXX: Some of this can be shared with labelTicket
	tracker, err := loaders.ForContext(ctx).TrackersByID.Load(trackerID)
	if err != nil {
		return nil, err
	} else if tracker == nil {
		return nil, fmt.Errorf("No such tracker")
	}
	if !tracker.CanTriage() {
		return nil, fmt.Errorf("Access denied")
	}

	ticket, err := loaders.ForContext(ctx).
		TicketsByTrackerID.Load([2]int{trackerID, ticketID})
	if err != nil {
		return nil, err
	} else if ticket == nil {
		return nil, fmt.Errorf("No such ticket")
	}

	label, err := loaders.ForContext(ctx).
		LabelsByID.Load(labelID)
	if err != nil {
		return nil, err
	} else if label == nil {
		return nil, fmt.Errorf("No such label")
	}

	user := auth.ForContext(ctx)
	part, err := loaders.ForContext(ctx).ParticipantsByUserID.Load(user.UserID)
	if err != nil {
		panic(err)
	}

	var event model.Event
	insertEvent := sq.Insert("event").
		PlaceholderFormat(sq.Dollar).
		Columns("created", "event_type", "ticket_id",
			"participant_id", "label_id").
		Values(sq.Expr("now() at time zone 'utc'"),
			model.EVENT_LABEL_REMOVED, ticket.PKID, part.ID, label.ID)

	columns := database.Columns(ctx, &event)
	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `
			DELETE FROM ticket_label
			WHERE ticket_id = $1 AND label_id = $2`,
			ticket.PKID, label.ID)
		if err != nil {
			return err
		}

		_, err = tx.ExecContext(ctx, `
			UPDATE ticket
			SET updated = NOW() at time zone 'utc'
			WHERE id = $1
		`, ticket.PKID)
		if err != nil {
			return nil
		}

		row := insertEvent.
			Suffix(`RETURNING ` + strings.Join(columns, ", ")).
			RunWith(tx).
			QueryRowContext(ctx)
		if err := row.Scan(database.Scan(ctx, &event)...); err != nil {
			return err
		}

		builder := NewEventBuilder(ctx, tx, part.ID, model.EVENT_LABEL_REMOVED).
			WithTicket(tracker, ticket)
		builder.InsertNotifications(event.ID, nil)
		return nil
	}); err != nil {
		return nil, err
	}
	webhooks.DeliverLegacyEventCreate(ctx, tracker, ticket, &event)
	return &event, nil
}

func (r *mutationResolver) CreateWebhook(ctx context.Context, config model.UserWebhookInput) (model.WebhookSubscription, error) {
	schema := server.ForContext(ctx).Schema
	if err := corewebhooks.Validate(schema, config.Query); err != nil {
		return nil, err
	}

	user := auth.ForContext(ctx)
	ac, err := corewebhooks.NewAuthConfig(ctx)
	if err != nil {
		return nil, err
	}

	var sub model.UserWebhookSubscription
	if len(config.Events) == 0 {
		return nil, fmt.Errorf("Must specify at least one event")
	}
	events := make([]string, len(config.Events))
	for i, ev := range config.Events {
		events[i] = ev.String()
		// TODO: gqlgen does not support doing anything useful with directives
		// on enums at the time of writing, so we have to do a little bit of
		// manual fuckery
		var access string
		switch ev {
		case model.WebhookEventTrackerCreated, model.WebhookEventTrackerUpdate,
			model.WebhookEventTrackerDeleted:
			access = "TRACKERS"
		case model.WebhookEventTicketCreated:
			access = "TICKETS"
		}
		if !user.Grants.Has(access, auth.RO) {
			return nil, fmt.Errorf("Insufficient access granted for webhook event %s", ev.String())
		}
	}

	u, err := url.Parse(config.URL)
	if err != nil {
		return nil, err
	} else if u.Host == "" {
		return nil, fmt.Errorf("Cannot use URL without host")
	} else if u.Scheme != "http" && u.Scheme != "https" {
		return nil, fmt.Errorf("Cannot use non-HTTP or HTTPS URL")
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := tx.QueryRowContext(ctx, `
			INSERT INTO gql_user_wh_sub (
				created, events, url, query,
				auth_method,
				token_hash, grants, client_id, expires,
				node_id,
				user_id
			) VALUES (
				NOW() at time zone 'utc',
				$1, $2, $3, $4, $5, $6, $7, $8, $9, $10
			) RETURNING id, url, query, events, user_id;`,
			pq.Array(events), config.URL, config.Query,
			ac.AuthMethod,
			ac.TokenHash, ac.Grants, ac.ClientID, ac.Expires, // OAUTH2
			ac.NodeID, // INTERNAL
			user.UserID)

		if err := row.Scan(&sub.ID, &sub.URL,
			&sub.Query, pq.Array(&sub.Events), &sub.UserID); err != nil {
			return err
		}
		return nil
	}); err != nil {
		return nil, err
	}

	return &sub, nil
}

func (r *mutationResolver) DeleteWebhook(ctx context.Context, id int) (model.WebhookSubscription, error) {
	var sub model.UserWebhookSubscription

	filter, err := corewebhooks.FilterWebhooks(ctx)
	if err != nil {
		return nil, err
	}

	if err := database.WithTx(ctx, nil, func(tx *sql.Tx) error {
		row := sq.Delete(`gql_user_wh_sub`).
			PlaceholderFormat(sq.Dollar).
			Where(sq.And{sq.Expr(`id = ?`, id), filter}).
			Suffix(`RETURNING id, url, query, events, user_id`).
			RunWith(tx).
			QueryRowContext(ctx)
		if err := row.Scan(&sub.ID, &sub.URL,
			&sub.Query, pq.Array(&sub.Events), &sub.UserID); err != nil {
			return err
		}
		return nil
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}

	return &sub, nil
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

func (r *queryResolver) Subscriptions(ctx context.Context, cursor *coremodel.Cursor) (*model.ActivitySubscriptionCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var subs []model.ActivitySubscription
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

	return &model.ActivitySubscriptionCursor{subs, cursor}, nil
}

func (r *queryResolver) UserWebhooks(ctx context.Context, cursor *coremodel.Cursor) (*model.WebhookSubscriptionCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	filter, err := corewebhooks.FilterWebhooks(ctx)
	if err != nil {
		return nil, err
	}

	var subs []model.WebhookSubscription
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		sub := (&model.UserWebhookSubscription{}).As(`sub`)
		query := database.
			Select(ctx, sub).
			From(`gql_user_wh_sub sub`).
			Where(filter)
		subs, cursor = sub.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.WebhookSubscriptionCursor{subs, cursor}, nil
}

func (r *queryResolver) UserWebhook(ctx context.Context, id int) (model.WebhookSubscription, error) {
	var sub model.UserWebhookSubscription

	filter, err := corewebhooks.FilterWebhooks(ctx)
	if err != nil {
		return nil, err
	}

	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		row := database.
			Select(ctx, &sub).
			From(`gql_user_wh_sub`).
			Where(sq.And{sq.Expr(`id = ?`, id), filter}).
			RunWith(tx).
			QueryRowContext(ctx)
		if err := row.Scan(database.Scan(ctx, &sub)...); err != nil {
			return err
		}
		return nil
	}); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}

	return &sub, nil
}

func (r *queryResolver) Webhook(ctx context.Context) (model.WebhookPayload, error) {
	raw, err := corewebhooks.Payload(ctx)
	if err != nil {
		return nil, err
	}
	payload, ok := raw.(model.WebhookPayload)
	if !ok {
		panic("Invalid webhook payload context")
	}
	return payload, nil
}

func (r *statusChangeResolver) Ticket(ctx context.Context, obj *model.StatusChange) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByID.Load(obj.TicketID)
}

func (r *statusChangeResolver) Editor(ctx context.Context, obj *model.StatusChange) (model.Entity, error) {
	return loaders.ForContext(ctx).EntitiesByParticipantID.Load(obj.ParticipantID)
}

func (r *ticketResolver) Submitter(ctx context.Context, obj *model.Ticket) (model.Entity, error) {
	return loaders.ForContext(ctx).EntitiesByParticipantID.Load(obj.SubmitterID)
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
	return loaders.ForContext(ctx).EntitiesByParticipantID.Load(obj.ParticipantID)
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

func (r *trackerResolver) Ticket(ctx context.Context, obj *model.Tracker, id int) (*model.Ticket, error) {
	return loaders.ForContext(ctx).TicketsByTrackerID.Load([2]int{obj.ID, id})
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

func (r *trackerResolver) DefaultACL(ctx context.Context, obj *model.Tracker) (*model.DefaultACL, error) {
	acl := &model.DefaultACL{}
	acl.SetBits(obj.DefaultAccess)
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
	panic(fmt.Errorf("not implemented")) // TODO
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
	return loaders.ForContext(ctx).EntitiesByParticipantID.Load(obj.ParticipantID)
}

func (r *userMentionResolver) Mentioned(ctx context.Context, obj *model.UserMention) (model.Entity, error) {
	return loaders.ForContext(ctx).EntitiesByParticipantID.Load(obj.MentionedID)
}

func (r *userWebhookSubscriptionResolver) Client(ctx context.Context, obj *model.UserWebhookSubscription) (*model.OAuthClient, error) {
	if obj.ClientID == nil {
		return nil, nil
	}
	return &model.OAuthClient{
		UUID: *obj.ClientID,
	}, nil
}

func (r *userWebhookSubscriptionResolver) Deliveries(ctx context.Context, obj *model.UserWebhookSubscription, cursor *coremodel.Cursor) (*model.WebhookDeliveryCursor, error) {
	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var deliveries []*model.WebhookDelivery
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		d := (&model.WebhookDelivery{}).
			WithName(`profile`).
			As(`delivery`)
		query := database.
			Select(ctx, d).
			From(`gql_user_wh_delivery delivery`).
			Where(`delivery.subscription_id = ?`, obj.ID)
		deliveries, cursor = d.QueryWithCursor(ctx, tx, query, cursor)
		return nil
	}); err != nil {
		return nil, err
	}

	return &model.WebhookDeliveryCursor{deliveries, cursor}, nil
}

func (r *userWebhookSubscriptionResolver) Sample(ctx context.Context, obj *model.UserWebhookSubscription, event *model.WebhookEvent) (string, error) {
	// TODO
	panic(fmt.Errorf("not implemented"))
}

func (r *webhookDeliveryResolver) Subscription(ctx context.Context, obj *model.WebhookDelivery) (model.WebhookSubscription, error) {
	if obj.Name == "" {
		panic("WebhookDelivery without name")
	}

	// XXX: This could use a loader but it's unlikely to be a bottleneck
	var sub model.WebhookSubscription
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		// XXX: This needs some work to generalize to other kinds of webhooks
		subscription := (&model.UserWebhookSubscription{}).As(`sub`)
		// Note: No filter needed because, if we have access to the delivery,
		// we also have access to the subscription.
		row := database.
			Select(ctx, subscription).
			From(`gql_user_wh_sub sub`).
			Where(`sub.id = ?`, obj.SubscriptionID).
			RunWith(tx).
			QueryRowContext(ctx)
		if err := row.Scan(database.Scan(ctx, subscription)...); err != nil {
			return err
		}
		sub = subscription
		return nil
	}); err != nil {
		return nil, err
	}
	return sub, nil
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

// UserWebhookSubscription returns api.UserWebhookSubscriptionResolver implementation.
func (r *Resolver) UserWebhookSubscription() api.UserWebhookSubscriptionResolver {
	return &userWebhookSubscriptionResolver{r}
}

// WebhookDelivery returns api.WebhookDeliveryResolver implementation.
func (r *Resolver) WebhookDelivery() api.WebhookDeliveryResolver { return &webhookDeliveryResolver{r} }

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
type userWebhookSubscriptionResolver struct{ *Resolver }
type webhookDeliveryResolver struct{ *Resolver }
