package webhooks

// XXX: No one uses the todo webhooks other than internal users, and they are
// really stupid and bad, and I am lacking in patience, so this is half-assed.

import (
	"context"
	"encoding/json"
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

	Submitter *ParticipantWebhookPayload `json:"submitter,omitempty"`
	Tracker   *TrackerWebhookPayload     `json:"tracker"`

	// In the interest of keeping the legacy code simple, these are left unused:
	Labels    []string      `json:"labels"`
	Assignees []interface{} `json:"assignees"`
}

type LabelWebhookPayload struct {
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

type CommentWebhookPayload struct {
	ID      int       `json:"id"`
	Created time.Time `json:"created"`
	Text    string    `json:"text"`
}

type EventWebhookPayload struct {
	ID            int       `json:"id"`
	Created       time.Time `json:"created"`
	EventType     []string  `json:"event_type"`
	OldStatus     *string   `json:"old_status"`
	OldResolution *string   `json:"old_resolution"`
	NewStatus     *string   `json:"new_status"`
	NewResolution *string   `json:"new_resolution"`

	User       *ParticipantWebhookPayload `json:"user"`
	Ticket     *TicketWebhookPayload      `json:"ticket"`
	Comment    *CommentWebhookPayload     `json:"comment"`
	Label      *LabelWebhookPayload       `json:"label"`
	ByUser     *ParticipantWebhookPayload `json:"by_user"`
	FromTicket *TicketWebhookPayload      `json:"from_ticket"`
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

func mkparticipant(part model.Entity) *ParticipantWebhookPayload {
	switch part := part.(type) {
	case *model.User:
		return &ParticipantWebhookPayload{
			Type:          "user",
			Name:          part.Username,
			CanonicalName: part.CanonicalName(),
		}
	case *model.EmailAddress:
		name := ""
		if part.Name != nil {
			name = *part.Name
		}
		return &ParticipantWebhookPayload{
			Type:    "email",
			Address: part.Mailbox,
			Name:    name,
		}
	case *model.ExternalUser:
		url := ""
		if part.ExternalURL != nil {
			url = *part.ExternalURL
		}
		return &ParticipantWebhookPayload{
			Type:        "external",
			ExternalID:  part.ExternalID,
			ExternalURL: url,
		}
	}
	panic("unreacahble")
}

func DeliverLegacyTrackerEvent(ctx context.Context,
	tracker *model.Tracker, ev string) {
	q := webhooks.LegacyForContext(ctx)
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
	q := webhooks.LegacyForContext(ctx)
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
	q := webhooks.LegacyForContext(ctx)

	payload := LabelWebhookPayload{
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
	q := webhooks.LegacyForContext(ctx)

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
	q := webhooks.LegacyForContext(ctx)

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
		Tracker: &TrackerWebhookPayload{
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

func mkEventTypes(eventType int) []string {
	var results []string
	if eventType&model.EVENT_CREATED != 0 {
		results = append(results, "created")
	}
	if eventType&model.EVENT_COMMENT != 0 {
		results = append(results, "comment")
	}
	if eventType&model.EVENT_STATUS_CHANGE != 0 {
		results = append(results, "status_change")
	}
	if eventType&model.EVENT_LABEL_ADDED != 0 {
		results = append(results, "label_added")
	}
	if eventType&model.EVENT_LABEL_REMOVED != 0 {
		results = append(results, "label_removed")
	}
	if eventType&model.EVENT_ASSIGNED_USER != 0 {
		results = append(results, "assigned_user")
	}
	if eventType&model.EVENT_UNASSIGNED_USER != 0 {
		results = append(results, "unassigned_user")
	}
	if eventType&model.EVENT_USER_MENTIONED != 0 {
		results = append(results, "user_mentioned")
	}
	if eventType&model.EVENT_TICKET_MENTIONED != 0 {
		results = append(results, "ticket_mentioned")
	}
	return results
}

func mkStatus(status *int) *string {
	if status == nil {
		return nil
	}
	var st string
	switch *status {
	case model.STATUS_REPORTED:
		st = "reported"
	case model.STATUS_CONFIRMED:
		st = "confirmed"
	case model.STATUS_IN_PROGRESS:
		st = "in_progress"
	case model.STATUS_PENDING:
		st = "pending"
	case model.STATUS_RESOLVED:
		st = "resolved"
	}
	return &st
}

func mkResolution(res *int) *string {
	if res == nil {
		return nil
	}
	var r string
	switch *res {
	case model.RESOLVED_UNRESOLVED:
		r = "unresolved"
	case model.RESOLVED_FIXED:
		r = "fixed"
	case model.RESOLVED_IMPLEMENTED:
		r = "implemented"
	case model.RESOLVED_WONT_FIX:
		r = "wont_fix"
	case model.RESOLVED_BY_DESIGN:
		r = "by_design"
	case model.RESOLVED_DUPLICATE:
		r = "duplicate"
	case model.RESOLVED_NOT_OUR_BUG:
		r = "not_our_bug"
	}
	return &r
}

func DeliverLegacyEventCreate(ctx context.Context,
	tracker *model.Tracker, ticket *model.Ticket, event *model.Event) {
	q := webhooks.LegacyForContext(ctx)

	part, err := loaders.ForContext(ctx).EntitiesByParticipantID.Load(event.ParticipantID)
	if err != nil || part == nil {
		panic("Invalid event participant")
	}

	payload := EventWebhookPayload{
		ID:        event.ID,
		Created:   event.Created,
		EventType: mkEventTypes(event.EventType),

		OldStatus:     mkStatus(event.OldStatus),
		OldResolution: mkResolution(event.OldResolution),
		NewStatus:     mkStatus(event.NewStatus),
		NewResolution: mkResolution(event.NewResolution),

		Ticket: &TicketWebhookPayload{
			ID:    ticket.PKID,
			Ref:   ticket.Ref(),
			Title: ticket.Subject,
			Tracker: &TrackerWebhookPayload{
				ID:      tracker.ID,
				Created: tracker.Created,
				Updated: tracker.Updated,
				Name:    tracker.Name,

				Owner: UserWebhookPayload{
					CanonicalName: "~" + ticket.OwnerName,
					Name:          ticket.OwnerName,
				},
			},
		},

		User: mkparticipant(part),
	}
	if event.ByParticipantID != nil {
		part, err := loaders.ForContext(ctx).
			EntitiesByParticipantID.Load(*event.ByParticipantID)
		if err != nil || part == nil {
			panic("Invalid event participant")
		}
		payload.ByUser = mkparticipant(part)
	}

	encoded, err := json.Marshal(&payload)
	if err != nil {
		panic(err) // Programmer error
	}

	query := sq.
		Select().
		From("tracker_webhook_subscription sub").
		Where("sub.tracker_id = ?", tracker.ID)
	q.Schedule(ctx, query, "tracker", "event:create", encoded)
	query = sq.
		Select().
		From("ticket_webhook_subscription sub").
		Where("sub.ticket_id = ?", ticket.PKID)
	q.Schedule(ctx, query, "ticket", "event:create", encoded)
}
