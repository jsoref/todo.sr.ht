package graph

// This file will be automatically regenerated based on the schema, any resolver implementations
// will be copied through when generating and any unknown code will be moved to the end.

import (
	"context"
	"fmt"

	model1 "git.sr.ht/~sircmpwn/core-go/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/api"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
)

func (r *queryResolver) Version(ctx context.Context) (*model.Version, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *queryResolver) Me(ctx context.Context) (*model.User, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *queryResolver) User(ctx context.Context, username string) (*model.User, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *queryResolver) Trackers(ctx context.Context, cursor *model1.Cursor) (*model.TrackerCursor, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *queryResolver) Tracker(ctx context.Context, id int) (*model.Tracker, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *queryResolver) TrackerByName(ctx context.Context, name string) (*model.Tracker, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *queryResolver) TrackerByOwner(ctx context.Context, owner string, repo string) (*model.Tracker, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *queryResolver) Events(ctx context.Context, cursor *model1.Cursor) (*model.EventCursor, error) {
	panic(fmt.Errorf("not implemented"))
}

func (r *queryResolver) Subscriptions(ctx context.Context, cursor *model1.Cursor) (*model.SubscriptionCursor, error) {
	panic(fmt.Errorf("not implemented"))
}

// Query returns api.QueryResolver implementation.
func (r *Resolver) Query() api.QueryResolver { return &queryResolver{r} }

type queryResolver struct{ *Resolver }
