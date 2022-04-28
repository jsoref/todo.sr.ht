package webhooks

import (
	"context"
	"time"

	"git.sr.ht/~sircmpwn/core-go/auth"
	"git.sr.ht/~sircmpwn/core-go/webhooks"
	sq "github.com/Masterminds/squirrel"
	"github.com/google/uuid"

	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
)

func deliverUserWebhook(ctx context.Context, event model.WebhookEvent,
	payload model.WebhookPayload, payloadUUID uuid.UUID) {
	q := webhooks.ForContext(ctx)
	userID := auth.ForContext(ctx).UserID
	query := sq.
		Select().
		From("gql_user_wh_sub sub").
		Where("sub.user_id = ?", userID)
	q.Schedule(ctx, query, "user", event.String(),
		payloadUUID, payload)
}

func deliverTrackerWebhook(ctx context.Context, trackerID int,
	event model.WebhookEvent, payload model.WebhookPayload, payloadUUID uuid.UUID) {
	q := webhooks.ForContext(ctx)
	userID := auth.ForContext(ctx).UserID
	query := sq.
		Select().
		From("gql_tracker_wh_sub sub").
		Where("sub.user_id = ? AND sub.tracker_id = ?", userID, trackerID)
	q.Schedule(ctx, query, "tracker", event.String(),
		payloadUUID, payload)
}

func DeliverUserTrackerEvent(ctx context.Context,
	event model.WebhookEvent, tracker *model.Tracker) {
	payloadUUID := uuid.New()
	payload := model.TrackerEvent{
		UUID:    payloadUUID.String(),
		Event:   event,
		Date:    time.Now().UTC(),
		Tracker: tracker,
	}
	deliverUserWebhook(ctx, event, &payload, payloadUUID)
}

func DeliverUserTicketEvent(ctx context.Context,
	event model.WebhookEvent, ticket *model.Ticket) {
	payloadUUID := uuid.New()
	payload := model.TicketEvent{
		UUID:   payloadUUID.String(),
		Event:  event,
		Date:   time.Now().UTC(),
		Ticket: ticket,
	}
	deliverUserWebhook(ctx, event, &payload, payloadUUID)
}

func DeliverTrackerEvent(ctx context.Context,
	event model.WebhookEvent, tracker *model.Tracker) {
	payloadUUID := uuid.New()
	payload := model.TrackerEvent{
		UUID:    payloadUUID.String(),
		Event:   event,
		Date:    time.Now().UTC(),
		Tracker: tracker,
	}
	deliverTrackerWebhook(ctx, tracker.ID, event, &payload, payloadUUID)
}

func DeliverTrackerLabelEvent(ctx context.Context,
	event model.WebhookEvent, trackerID int, label *model.Label) {
	payloadUUID := uuid.New()
	payload := model.LabelEvent{
		UUID:  payloadUUID.String(),
		Event: event,
		Date:  time.Now().UTC(),
		Label: label,
	}
	deliverTrackerWebhook(ctx, trackerID, event, &payload, payloadUUID)
}

func DeliverTrackerTicketEvent(ctx context.Context,
	event model.WebhookEvent, trackerID int, ticket *model.Ticket) {
	payloadUUID := uuid.New()
	payload := model.TicketEvent{
		UUID:   payloadUUID.String(),
		Event:  event,
		Date:   time.Now().UTC(),
		Ticket: ticket,
	}
	deliverTrackerWebhook(ctx, trackerID, event, &payload, payloadUUID)
}

func DeliverTrackerEventCreated(ctx context.Context, trackerID int, newEvent *model.Event) {
	event := model.WebhookEventEventCreated
	payloadUUID := uuid.New()
	payload := model.EventCreated{
		UUID:     payloadUUID.String(),
		Event:    event,
		Date:     time.Now().UTC(),
		NewEvent: newEvent,
	}
	deliverTrackerWebhook(ctx, trackerID, event, &payload, payloadUUID)
}
