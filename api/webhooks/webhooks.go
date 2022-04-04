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

func DeliverTrackerEvent(ctx context.Context,
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

func DeliverTicketEvent(ctx context.Context,
	event model.WebhookEvent, ticket *model.Ticket) {
	payloadUUID := uuid.New()
	payload := model.TicketEvent{
		UUID:    payloadUUID.String(),
		Event:   event,
		Date:    time.Now().UTC(),
		Ticket: ticket,
	}
	deliverUserWebhook(ctx, event, &payload, payloadUUID)
}
