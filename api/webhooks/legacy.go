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
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/loaders"
)

type UserWebhookPayload struct {
	Name          string `json:"name"`
	CanonicalName string `json:"canonical_name"`
}

type ParticipantWebhookPayload struct {
	Type string `json:"type"`

	// User
	Name          string `json:"name,omitempty"`
	CanonicalName string `json:"canonical_name,omitempty"`

	// Email address
	Address string `json:"address,omitempty"`

	// External
	ExternalID  string `json:"external_id,omitempty"`
	ExternalURL string `json:"external_url,omitempty"`
}

type TrackerWebhookPayload struct {
	ID            int       `json:"id"`
	Created       time.Time `json:"created"`
	Updated       time.Time `json:"updated"`
	Name          string    `json:"name"`
	Description   *string   `json:"description,omitempty"`
	Visibility    string    `json:"visibility,omitempty"`
	DefaultAccess []string  `json:"default_access,omitempty"`

	Owner UserWebhookPayload `json:"owner"`
}

type TicketWebhookPayload struct {
	ID          int       `json:"id"`
	Ref         string    `json:"ref"`
	Created     time.Time `json:"created"`
	Updated     time.Time `json:"updated"`
	Title       string    `json:"title"`
	Description *string   `json:"description"`
	Status      string    `json:"status"`
	Resolution  string    `json:"resolution"`

	Submitter ParticipantWebhookPayload `json:"submitter"`
	Tracker   TrackerWebhookPayload     `json:"tracker"`

	// In the interest of keeping the legacy code simple, these are left unused:
	Labels    []string      `json:"labels"`
	Assignees []interface{} `json:"assignees"`
}

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

func mkparticipant(part model.Entity) ParticipantWebhookPayload {
	switch part := part.(type) {
	case *model.User:
		return ParticipantWebhookPayload{
			Type:          "user",
			Name:          part.Username,
			CanonicalName: part.CanonicalName(),
		}
	case *model.EmailAddress:
		name := ""
		if part.Name != nil {
			name = *part.Name
		}
		return ParticipantWebhookPayload{
			Type:    "email",
			Address: part.Mailbox,
			Name:    name,
		}
	case *model.ExternalUser:
		url := ""
		if part.ExternalURL != nil {
			url = *part.ExternalURL
		}
		return ParticipantWebhookPayload{
			Type:        "external",
			ExternalID:  part.ExternalID,
			ExternalURL: url,
		}
	}
	panic("unreacahble")
}

func DeliverLegacyTrackerEvent(ctx context.Context,
	tracker *model.Tracker, ev string) {
	q, ok := ctx.Value(legacyWebhooksCtxKey).(*webhooks.LegacyQueue)
	if !ok {
		panic("No legacy webhooks worker for this context")
	}

	user := auth.ForContext(ctx)
	if user.UserID != tracker.OwnerID {
		panic("Submitting webhook for another user's context (why?)")
	}

	payload := TrackerWebhookPayload{
		ID:            tracker.ID,
		Created:       tracker.Created,
		Updated:       tracker.Updated,
		Name:          tracker.Name,
		Description:   tracker.Description,
		Visibility:    strings.ToLower(tracker.Visibility.String()),
		DefaultAccess: mkaccess(tracker),

		Owner: UserWebhookPayload{
			CanonicalName: "~" + user.Username,
			Name:          user.Username,
		},
	}

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

func DeliverLegacyLabelDelete(ctx context.Context, trackerID, labelID int) {
	q, ok := ctx.Value(legacyWebhooksCtxKey).(*webhooks.LegacyQueue)
	if !ok {
		panic("No legacy webhooks worker for this context")
	}

	// It occurs to me that this webhook is completely useless given that the
	// legacy API doesn't expose label IDs to the user
	type WebhookPayload struct {
		ID int `json:"id"`
	}

	payload := WebhookPayload{labelID}

	encoded, err := json.Marshal(&payload)
	if err != nil {
		panic(err) // Programmer error
	}

	query := sq.
		Select().
		From("tracker_webhook_subscription sub").
		Where("sub.tracker_id = ?", trackerID)
	q.Schedule(ctx, query, "tracker", "label:delete", encoded)
}

func DeliverLegacyTicketCreate(ctx context.Context,
	tracker *model.Tracker, ticket *model.Ticket) {
	q, ok := ctx.Value(legacyWebhooksCtxKey).(*webhooks.LegacyQueue)
	if !ok {
		panic("No legacy webhooks worker for this context")
	}

	part, err := loaders.ForContext(ctx).EntitiesByParticipantID.Load(ticket.SubmitterID)
	if err != nil || part == nil {
		panic("Invalid ticket participant")
	}

	payload := TicketWebhookPayload{
		ID:          ticket.ID,
		Ref:         ticket.Ref(),
		Created:     ticket.Created,
		Updated:     ticket.Updated,
		Title:       ticket.Subject,
		Description: ticket.Body,
		Status:      ticket.Status().String(),
		Resolution:  ticket.Resolution().String(),

		Submitter: mkparticipant(part),
		Tracker: TrackerWebhookPayload{
			ID:      tracker.ID,
			Created: tracker.Created,
			Updated: tracker.Updated,
			Name:    tracker.Name,

			Owner: UserWebhookPayload{
				CanonicalName: "~" + ticket.OwnerName,
				Name:          ticket.OwnerName,
			},
		},
	}

	encoded, err := json.Marshal(&payload)
	if err != nil {
		panic(err) // Programmer error
	}

	query := sq.
		Select().
		From("tracker_webhook_subscription sub").
		Where("sub.tracker_id = ?", tracker.ID)
	q.Schedule(ctx, query, "tracker", "ticket:create", encoded)

	if user, ok := part.(*model.User); ok {
		query := sq.
			Select().
			From("user_webhook_subscription sub").
			Where("sub.user_id = ?", user.ID)
		q.Schedule(ctx, query, "user", "ticket:create", encoded)
	}
}
