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
		panic("No legacy user webhooks worker for this context")
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
