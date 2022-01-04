package graph

import (
	"context"
	"database/sql"

	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/loaders"
)

type EventBuilder struct {
	ctx         context.Context
	tx          *sql.Tx
	eventType   uint
	submitterID int
	tracker     *model.Tracker
	ticket      *model.Ticket

	mentionedParticipants []int
	mentions *Mentions
}

// Creates a new event builder for a given submitter (a participant ID) and a
// certain event type, using the provided context and transaction. This is used
// to provide a common implementation for creating events and notifications,
// building up the list of implicated participants over time.
//
// The order in which you call the subsequent functions is important:
// 1. WithTicket
// 2. AddMentions
// 3. InsertSubscriptions
// 4. InsertNotifications
func NewEventBuilder(ctx context.Context, tx *sql.Tx,
	submitterID int, eventType uint) *EventBuilder {
	// Create a temporary table of all participants affected by this
	// submission. This includes everyone who will be notified about it.
	_, err := tx.ExecContext(ctx, `
		CREATE TEMP TABLE event_participant
		ON COMMIT DROP
		AS (SELECT
			-- The affected participant:
			$1::INTEGER AS participant_id,
			-- Events they should be notified of:
			$2::INTEGER AS event_type,
			-- Should they be subscribed to this ticket?
			true AS subscribe
		);
	`, submitterID, eventType)
	if err != nil {
		panic(err)
	}

	return &EventBuilder{
		ctx:         ctx,
		tx:          tx,
		eventType:   eventType,
		submitterID: submitterID,
	}
}

// Associates this event with a ticket and implicates the submitter for the
// appropriate events and notifications.
func (eb *EventBuilder) WithTicket(
	tracker *model.Tracker, ticket *model.Ticket) *EventBuilder {
	eb.tracker = tracker
	eb.ticket = ticket
	_, err := eb.tx.ExecContext(eb.ctx, `
		INSERT INTO event_participant (
			participant_id, event_type, subscribe
		)
		SELECT sub.participant_id, $1, false
		FROM ticket_subscription sub
		WHERE sub.tracker_id = $2 OR sub.ticket_id = $3
	`, eb.eventType, tracker.ID, ticket.PKID)
	if err != nil {
		panic(err)
	}
	return eb
}

// Adds mentions to this event builder
func (eb *EventBuilder) AddMentions(mentions *Mentions) {
	eb.mentions = mentions
	for user, _ := range mentions.Users {
		part, err := loaders.ForContext(eb.ctx).ParticipantsByUsername.Load(user)
		if err != nil {
			panic(err)
		}
		if part == nil {
			continue
		}
		_, err = eb.tx.ExecContext(eb.ctx, `
			INSERT INTO event_participant (
				participant_id, event_type, subscribe
			) VALUES (
				$1, $2, true
			);
		`, part.ID, model.EVENT_USER_MENTIONED)
		if err != nil {
			panic(err)
		}
		eb.mentionedParticipants = append(eb.mentionedParticipants, part.ID)
	}
}

// Creates subscriptions for all affected users
func (eb *EventBuilder) InsertSubscriptions() {
	_, err := eb.tx.ExecContext(eb.ctx, `
		INSERT INTO ticket_subscription (
			created, updated, ticket_id, participant_id
		)
		SELECT
			NOW() at time zone 'utc',
			NOW() at time zone 'utc',
			$1, participant_id
		FROM event_participant
		WHERE subscribe = true
		ON CONFLICT ON CONSTRAINT subscription_ticket_participant_uq
		DO NOTHING;
	`, eb.ticket.PKID)
	if err != nil {
		panic(err)
	}
}

// Adds event_notification records for all affected users and inserts
// ancillary events (such as mentions) and their notifications.
func (eb *EventBuilder) InsertNotifications(eventID int, commentID *int) {
	_, err := eb.tx.ExecContext(eb.ctx, `
		INSERT INTO event_notification (created, event_id, user_id)
		SELECT
			NOW() at time zone 'utc',
			$1, part.user_id
		FROM event_participant ev
		JOIN participant part ON part.id = ev.participant_id
		WHERE part.user_id IS NOT NULL AND ev.event_type = $2;
	`, eventID, eb.eventType)
	if err != nil {
		panic(err)
	}

	if eb.mentions == nil {
		return
	}

	for _, id := range eb.mentionedParticipants {
		var eventID int
		row := eb.tx.QueryRowContext(eb.ctx, `
			INSERT INTO event (
				created, event_type, participant_id, by_participant_id,
				ticket_id, from_ticket_id, comment_id
			) VALUES (
				NOW() at time zone 'utc',
				$1, $2, $3, $4, $4, $5
			) RETURNING id;`,
			model.EVENT_USER_MENTIONED, id, eb.submitterID,
			eb.ticket.PKID, commentID)
		if err := row.Scan(&eventID); err != nil {
			panic(err)
		}
		_, err := eb.tx.ExecContext(eb.ctx, `
			INSERT INTO event_notification (created, event_id, user_id)
			SELECT
				NOW() at time zone 'utc',
				$1, part.user_id
			FROM event_participant ev
			JOIN participant part ON part.id = ev.participant_id
			WHERE part.user_id IS NOT NULL AND ev.event_type = $2;
		`, eventID, model.EVENT_USER_MENTIONED)
		if err != nil {
			panic(err)
		}
	}

	for _, target := range eb.mentions.Tickets {
		_, err := eb.tx.ExecContext(eb.ctx, `
			WITH target AS (
				SELECT tk.id
				FROM ticket tk
				JOIN tracker tr ON tk.tracker_id = tr.id
				JOIN "user" u ON u.id = tr.owner_id
				WHERE u.username = $1 AND tr.name = $2 AND tk.scoped_id = $3
			)
			INSERT INTO event (
				created, event_type, by_participant_id, ticket_id,
				from_ticket_id, comment_id
			) VALUES (
				NOW() at time zone 'utc',
				$4, $5, (SELECT id FROM target), $6, $7
			)`,
			target.OwnerName, target.TrackerName, target.ID,
			model.EVENT_TICKET_MENTIONED, eb.submitterID, eb.ticket.PKID,
			commentID)
		if err != nil {
			panic(err)
		}
	}
}
