package graph

// This file will be automatically regenerated based on the schema, any resolver implementations
// will be copied through when generating and any unknown code will be moved to the end.

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	"git.sr.ht/~sircmpwn/core-go/auth"
	"git.sr.ht/~sircmpwn/core-go/database"
	coremodel "git.sr.ht/~sircmpwn/core-go/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/api"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/loaders"
)

func (r *assignmentResolver) Ticket(ctx context.Context, obj *model.Assignment) (*model.Ticket, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *assignmentResolver) Entity(ctx context.Context, obj *model.Assignment) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *assignmentResolver) Assigner(ctx context.Context, obj *model.Assignment) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *assignmentResolver) Assignee(ctx context.Context, obj *model.Assignment) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *commentResolver) Ticket(ctx context.Context, obj *model.Comment) (*model.Ticket, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *commentResolver) Entity(ctx context.Context, obj *model.Comment) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *commentResolver) Text(ctx context.Context, obj *model.Comment) (string, error) {
	comment, err := loaders.ForContext(ctx).CommentsByID.Load(obj.Database.ID)
	return comment.Database.Text, err
}

func (r *commentResolver) Authenticity(ctx context.Context, obj *model.Comment) (model.Authenticity, error) {
	comment, err := loaders.ForContext(ctx).CommentsByID.Load(obj.Database.ID)
	return comment.Database.Authenticity, err
}

func (r *commentResolver) SuperceededBy(ctx context.Context, obj *model.Comment) (*model.Comment, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *createdResolver) Ticket(ctx context.Context, obj *model.Created) (*model.Ticket, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *createdResolver) Entity(ctx context.Context, obj *model.Created) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *eventResolver) Entity(ctx context.Context, obj *model.Event) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *eventResolver) Ticket(ctx context.Context, obj *model.Event) (*model.Ticket, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *eventResolver) Tracker(ctx context.Context, obj *model.Event) (*model.Tracker, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *labelUpdateResolver) Ticket(ctx context.Context, obj *model.LabelUpdate) (*model.Ticket, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *labelUpdateResolver) Entity(ctx context.Context, obj *model.LabelUpdate) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *labelUpdateResolver) Label(ctx context.Context, obj *model.LabelUpdate) (*model.Label, error) {
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
	panic(fmt.Errorf("not implemented"))
}

func (r *statusChangeResolver) Ticket(ctx context.Context, obj *model.StatusChange) (*model.Ticket, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *statusChangeResolver) Entity(ctx context.Context, obj *model.StatusChange) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *ticketResolver) Submitter(ctx context.Context, obj *model.Ticket) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *ticketResolver) Tracker(ctx context.Context, obj *model.Ticket) (*model.Tracker, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *ticketResolver) Labels(ctx context.Context, obj *model.Ticket) ([]*model.Label, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *ticketResolver) Assignees(ctx context.Context, obj *model.Ticket) ([]model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *ticketMentionResolver) Ticket(ctx context.Context, obj *model.TicketMention) (*model.Ticket, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *ticketMentionResolver) Entity(ctx context.Context, obj *model.TicketMention) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *ticketMentionResolver) Mentioned(ctx context.Context, obj *model.TicketMention) (*model.Ticket, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *trackerResolver) Owner(ctx context.Context, obj *model.Tracker) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
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
	panic(fmt.Errorf("not implemented"))
}

func (r *trackerResolver) Acls(ctx context.Context, obj *model.Tracker, cursor *coremodel.Cursor) (*model.ACLCursor, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *userResolver) Trackers(ctx context.Context, obj *model.User, cursor *coremodel.Cursor) (*model.TrackerCursor, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *userMentionResolver) Ticket(ctx context.Context, obj *model.UserMention) (*model.Ticket, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *userMentionResolver) Entity(ctx context.Context, obj *model.UserMention) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *userMentionResolver) Mentioned(ctx context.Context, obj *model.UserMention) (model.Entity, error) {
	panic(fmt.Errorf("not implemented"))
}

// Assignment returns api.AssignmentResolver implementation.
func (r *Resolver) Assignment() api.AssignmentResolver { return &assignmentResolver{r} }

// Comment returns api.CommentResolver implementation.
func (r *Resolver) Comment() api.CommentResolver { return &commentResolver{r} }

// Created returns api.CreatedResolver implementation.
func (r *Resolver) Created() api.CreatedResolver { return &createdResolver{r} }

// Event returns api.EventResolver implementation.
func (r *Resolver) Event() api.EventResolver { return &eventResolver{r} }

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

// Tracker returns api.TrackerResolver implementation.
func (r *Resolver) Tracker() api.TrackerResolver { return &trackerResolver{r} }

// User returns api.UserResolver implementation.
func (r *Resolver) User() api.UserResolver { return &userResolver{r} }

// UserMention returns api.UserMentionResolver implementation.
func (r *Resolver) UserMention() api.UserMentionResolver { return &userMentionResolver{r} }

type assignmentResolver struct{ *Resolver }
type commentResolver struct{ *Resolver }
type createdResolver struct{ *Resolver }
type eventResolver struct{ *Resolver }
type labelUpdateResolver struct{ *Resolver }
type queryResolver struct{ *Resolver }
type statusChangeResolver struct{ *Resolver }
type ticketResolver struct{ *Resolver }
type ticketMentionResolver struct{ *Resolver }
type trackerResolver struct{ *Resolver }
type userResolver struct{ *Resolver }
type userMentionResolver struct{ *Resolver }
