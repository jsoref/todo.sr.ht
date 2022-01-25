import json
from collections import OrderedDict
from datetime import datetime, timezone
from srht.crypto import verify_payload
from srht.config import get_origin
from srht.database import db
from todosrht.tickets import submit_ticket
from todosrht.tickets import get_participant_for_email
from todosrht.tickets import get_participant_for_external
from todosrht.tickets import get_participant_for_user
from todosrht.types import Event, EventType, Tracker, Ticket, TicketComment
from todosrht.types import ParticipantType, User
from todosrht.types import Label, TicketLabel
from todosrht.types import TicketStatus, TicketResolution
from todosrht.types import TicketAuthenticity
from todosrht.webhooks import worker

our_upstream = get_origin("todo.sr.ht", external=True)

def _parse_date(date):
    date = datetime.fromisoformat(date)
    date = date.astimezone(timezone.utc).replace(tzinfo=None)
    return date

def _import_participant(pdata, upstream):
    if pdata["type"] == "user":
        if upstream == our_upstream:
            user = User.query.filter(User.username == pdata["name"]).first()
        else:
            user = None

        if user:
            submitter = get_participant_for_user(user)
        else:
            submitter = get_participant_for_external(
                    pdata["canonical_name"],
                    upstream + "/" + pdata["canonical_name"])
    elif pdata["type"] == "email":
        submitter = get_participant_for_email(pdata["address"], pdata["name"])
    elif pdata["type"] == "external":
        submitter = get_participant_for_external(
                pdata["external_id"], pdata["external_url"])
    return submitter

def _import_comment(ticket, event, edata):
    cdata = edata["comment"]
    comment = TicketComment()
    submitter = _import_participant(cdata["submitter"], edata["upstream"])
    comment.submitter_id = submitter.id
    comment.ticket_id = ticket.id
    comment.text = cdata["text"]
    comment.authenticity = TicketAuthenticity.unauthenticated
    comment.created = _parse_date(cdata["created"])
    comment.updated = comment.created
    comment._no_autoupdate = True
    signature, nonce = edata.get("X-Payload-Signature"), edata.get("X-Payload-Nonce")
    if (signature and nonce
            and edata["upstream"] == our_upstream
            and submitter.participant_type == ParticipantType.user):
        # TODO: Validate signatures from trusted third-parties
        sigdata = OrderedDict({
            "comment": comment.text,
            "id": edata["id"], # not important to verify this
            "ticket": edata["ticket"]["ref"], # not important to verify this
            "user": submitter.user.canonical_name,
            "upstream": edata["upstream"],
        })
        sigdata = json.dumps(sigdata)
        if verify_payload(sigdata, signature, nonce):
            comment.authenticity = TicketAuthenticity.authentic
        else:
            comment.authenticity = TicketAuthenticity.tampered
    ticket.comment_count += 1
    db.session.add(comment)
    db.session.flush()
    event.comment_id = comment.id

def _tracker_import(dump, tracker):
    ldict = dict()
    for ldata in dump["labels"]:
        label = Label()
        label.tracker_id = tracker.id
        label.name = ldata["name"]
        label.color = ldata["colors"]["background"]
        label.text_color = ldata["colors"]["text"]
        db.session.add(label)
        db.session.flush()
        ldict[label.name] = label.id
    tickets = sorted(dump["tickets"], key=lambda t: t["id"])
    for tdata in tickets:
        for field in [
                "id", "title", "created", "description", "status", "resolution",
                "labels", "assignees", "upstream", "events", "submitter",
            ]:
            if not field in tdata:
                print("Invalid ticket data")
                continue
        ticket = Ticket.query.filter(
                Ticket.tracker_id == tracker.id,
                Ticket.scoped_id == tdata["id"]).one_or_none()
        if ticket:
            print(f"Ticket {tdata['id']} already imported - skipping")
            continue
        submitter = _import_participant(tdata["submitter"], tdata["upstream"])
        ticket = submit_ticket(tracker, submitter,
                tdata["title"], tdata["description"], importing=True)
        try:
            created = _parse_date(tdata["created"])
        except ValueError:
            created = datetime.utcnow()
        ticket._no_autoupdate = True
        ticket.created = created
        ticket.updated = created
        ticket.status = TicketStatus[tdata["status"]]
        ticket.resolution = TicketResolution[tdata["resolution"]]
        ticket.authenticity = TicketAuthenticity.unauthenticated
        for label in tdata["labels"]:
            tl = TicketLabel()
            tl.ticket_id = ticket.id
            tl.label_id = ldict.get(label)
            tl.user_id = tracker.owner_id
            db.session.add(tl)
        # TODO: assignees
        signature, nonce = tdata.get("X-Payload-Signature"), tdata.get("X-Payload-Nonce")
        if (signature and nonce
                and tdata["upstream"] == our_upstream
                and submitter.participant_type == ParticipantType.user):
            # TODO: Validate signatures from trusted third-parties
            sigdata = OrderedDict({
                "description": ticket.description,
                "ref": tdata["ref"], # not important to verify this
                "submitter": ticket.submitter.user.canonical_name,
                "title": ticket.title,
                "upstream": tdata["upstream"],
            })
            sigdata = json.dumps(sigdata)
            if verify_payload(sigdata, signature, nonce):
                ticket.authenticity = TicketAuthenticity.authentic
            else:
                ticket.authenticity = TicketAuthenticity.tampered
        for edata in tdata.get("events", []):
            for field in [
                "created", "event_type", "old_status", "new_status",
                "old_resolution", "new_resolution", "user", "ticket",
                "comment", "label", "by_user", "from_ticket", "upstream",
            ]:
                if not field in edata:
                    print("Invalid ticket event")
                    return
            event = Event()
            for etype in edata["event_type"]:
                if event.event_type == None:
                    event.event_type = EventType[etype]
                else:
                    event.event_type |= EventType[etype]
            if event.event_type == None:
                print("Invalid ticket event")
                continue
            if EventType.comment in event.event_type:
                _import_comment(ticket, event, edata)
            if EventType.status_change in event.event_type:
                if edata["old_status"]:
                    event.old_status = TicketStatus[edata["old_status"]]
                if edata["new_status"]:
                    event.new_status = TicketStatus[edata["new_status"]]
            if EventType.label_added in event.event_type:
                event.label_id = ldict.get(edata["label"])
                if not event.label_id:
                    continue
            if EventType.label_removed in event.event_type:
                event.label_id = ldict.get(edata["label"])
                if not event.label_id:
                    continue
            if EventType.assigned_user in event.event_type:
                by_participant = _import_participant(
                        edata["by_user"], edata["upstream"])
                event.by_participant_id = by_participant.id
            if EventType.unassigned_user in event.event_type:
                by_participant = _import_participant(
                        edata["by_user"], edata["upstream"])
                event.by_participant_id = by_participant.id
            if EventType.user_mentioned in event.event_type:
                continue # Magic event type, do not import
            if EventType.ticket_mentioned in event.event_type:
                continue # TODO: Could reference tickets imported in later iters
            event.created = _parse_date(edata["created"])
            event.updated = event.created
            event._no_autoupdate = True
            event.ticket_id = ticket.id
            participant = _import_participant(edata["user"], edata["upstream"])
            event.participant_id = participant.id
            db.session.add(event)
        print(f"Imported {ticket.ref()}")

@worker.task
def tracker_import(dump, tracker_id):
    tracker = Tracker.query.get(tracker_id)
    try:
        _tracker_import(dump, tracker)
    except:
        # TODO: Tell user that the import failed?
        db.session.rollback()
        tracker = Tracker.query.get(tracker_id)
        raise
    finally:
        tracker.import_in_progress = False
        db.session.commit()
