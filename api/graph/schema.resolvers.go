package graph

// This file will be automatically regenerated based on the schema, any resolver implementations
// will be copied through when generating and any unknown code will be moved to the end.

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	"git.sr.ht/~sircmpwn/core-go/auth"
	"git.sr.ht/~sircmpwn/core-go/database"
	coremodel "git.sr.ht/~sircmpwn/core-go/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/api"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/loaders"
	sq "github.com/Masterminds/squirrel"
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

func (r *commentResolver) SuperceededBy(ctx context.Context, obj *model.Comment) (*model.Comment, error) {
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

func (r *ticketResolver) ACL(ctx context.Context, obj *model.Ticket) (model.ACL, error) {
	panic(fmt.Errorf("not implemented"))
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
	if !obj.CanBrowse() {
		return nil, errors.New("You do not have permission to browse this tracker")
	}

	if cursor == nil {
		cursor = coremodel.NewCursor(nil)
	}

	var tickets []*model.Ticket
	if err := database.WithTx(ctx, &sql.TxOptions{
		Isolation: 0,
		ReadOnly:  true,
	}, func(tx *sql.Tx) error {
		ticket := (&model.Ticket{}).As(`tk`)
		query := database.
			Select(ctx, ticket).
			From(`ticket tk`).
			Where(`tk.tracker_id = ?`, obj.ID)
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

func (r *trackerResolver) Acls(ctx context.Context, obj *model.Tracker, cursor *coremodel.Cursor) (*model.ACLCursor, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *trackerResolver) Subscription(ctx context.Context, obj *model.Tracker) (*model.TrackerSubscription, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *trackerResolver) ACL(ctx context.Context, obj *model.Tracker) (model.ACL, error) {
	panic(fmt.Errorf("not implemented"))
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
					sq.Expr(`tr.default_user_perms > 0`),
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
type queryResolver struct{ *Resolver }
type statusChangeResolver struct{ *Resolver }
type ticketResolver struct{ *Resolver }
type ticketMentionResolver struct{ *Resolver }
type ticketSubscriptionResolver struct{ *Resolver }
type trackerResolver struct{ *Resolver }
type trackerSubscriptionResolver struct{ *Resolver }
type userResolver struct{ *Resolver }
type userMentionResolver struct{ *Resolver }
