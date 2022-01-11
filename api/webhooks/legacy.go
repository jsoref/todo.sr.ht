package webhooks

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"git.sr.ht/~sircmpwn/core-go/auth"
	"git.sr.ht/~sircmpwn/core-go/webhooks"
	sq "github.com/Masterminds/squirrel"

	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
)

func NewLegacyQueue() *webhooks.LegacyQueue {
	return webhooks.NewLegacyQueue()
}

var legacyWebhooksCtxKey = &contextKey{"legacy-webhooks"}

type contextKey struct {
	name string
}

func LegacyMiddleware(
	queue *webhooks.LegacyQueue,
) func(next http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			ctx := context.WithValue(r.Context(), legacyWebhooksCtxKey, queue)
			r = r.WithContext(ctx)
			next.ServeHTTP(w, r)
		})
	}
}

func mkaccess(tracker *model.Tracker) []string {
	var items []string
	if tracker.DefaultAccess&model.ACCESS_BROWSE != 0 {
		items = append(items, "browse")
	}
	if tracker.DefaultAccess&model.ACCESS_SUBMIT != 0 {
		items = append(items, "submit")
	}
	if tracker.DefaultAccess&model.ACCESS_COMMENT != 0 {
		items = append(items, "comment")
	}
	if tracker.DefaultAccess&model.ACCESS_EDIT != 0 {
		items = append(items, "edit")
	}
	if tracker.DefaultAccess&model.ACCESS_TRIAGE != 0 {
		items = append(items, "triage")
	}
	return items
}

func DeliverLegacyTrackerEvent(ctx context.Context,
	tracker *model.Tracker, ev string) {
	q, ok := ctx.Value(legacyWebhooksCtxKey).(*webhooks.LegacyQueue)
	if !ok {
		panic("No legacy webhooks worker for this context")
	}

	type WebhookPayload struct {
		ID            int       `json:"id"`
		Created       time.Time `json:"created"`
		Updated       time.Time `json:"updated"`
		Name          string    `json:"name"`
		Description   *string   `json:"name"`
		Visibility    string    `json:"visibility"`
		DefaultAccess []string  `json:"default_access"`

		Owner struct {
			CanonicalName string `json:"canonical_name"`
			Name          string `json:"name"`
		} `json:"owner"`
	}

	payload := WebhookPayload{
		ID:            tracker.ID,
		Created:       tracker.Created,
		Updated:       tracker.Updated,
		Name:          tracker.Name,
		Description:   tracker.Description,
		Visibility:    strings.ToLower(tracker.Visibility.String()),
		DefaultAccess: mkaccess(tracker),
	}

	user := auth.ForContext(ctx)
	if user.UserID != tracker.OwnerID {
		panic("Submitting webhook for another user's context (why?)")
	}
	payload.Owner.CanonicalName = "~" + user.Username
	payload.Owner.Name = user.Username

	encoded, err := json.Marshal(&payload)
	if err != nil {
		panic(err) // Programmer error
	}

	query := sq.
		Select().
		From("user_webhook_subscription sub").
		Where("sub.user_id = ?", user.UserID)
	q.Schedule(ctx, query, "user", ev, encoded)
}

func DeliverLegacyTrackerDelete(ctx context.Context, trackerId, userId int) {
	q, ok := ctx.Value(legacyWebhooksCtxKey).(*webhooks.LegacyQueue)
	if !ok {
		panic("No legacy webhooks worker for this context")
	}

	type WebhookPayload struct {
		ID int `json:"id"`
	}

	payload := WebhookPayload{trackerId}

	encoded, err := json.Marshal(&payload)
	if err != nil {
		panic(err) // Programmer error
	}

	query := sq.
		Select().
		From("user_webhook_subscription sub").
		Where("sub.user_id = ?", userId)
	q.Schedule(ctx, query, "user", "tracker:delete", encoded)
}

func DeliverLegacyLabelCreate(ctx context.Context,
	tracker *model.Tracker, label *model.Label) {
	q, ok := ctx.Value(legacyWebhooksCtxKey).(*webhooks.LegacyQueue)
	if !ok {
		panic("No legacy webhooks worker for this context")
	}

	type WebhookPayload struct {
		Name    string    `json:"name"`
		Created time.Time `json:"created"`

		Colors struct {
			Background string `json:"background"`
			Text       string `json:"text"`
		} `json:"colors"`

		Tracker struct {
			ID      int       `json:"id"`
			Created time.Time `json:"created"`
			Updated time.Time `json:"updated"`
			Name    string    `json:"name"`

			Owner struct {
				CanonicalName string `json:"canonical_name"`
				Name          string `json:"name"`
			} `json:"owner"`
		} `json:"tracker"`
	}

	payload := WebhookPayload{
		Name:    label.Name,
		Created: label.Created,
	}
	payload.Colors.Background = label.BackgroundColor
	payload.Colors.Text = label.ForegroundColor
	payload.Tracker.ID = tracker.ID
	payload.Tracker.Created = tracker.Created
	payload.Tracker.Updated = tracker.Updated
	payload.Tracker.Name = tracker.Name

	user := auth.ForContext(ctx)
	if user.UserID != tracker.OwnerID {
		panic("Submitting webhook for another user's context (why?)")
	}
	payload.Tracker.Owner.CanonicalName = "~" + user.Username
	payload.Tracker.Owner.Name = user.Username

	encoded, err := json.Marshal(&payload)
	if err != nil {
		panic(err) // Programmer error
	}

	query := sq.
		Select().
		From("tracker_webhook_subscription sub").
		Where("sub.tracker_id = ?", tracker.ID)
	q.Schedule(ctx, query, "tracker", "label:create", encoded)
}
