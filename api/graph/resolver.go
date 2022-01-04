package graph

import (
	"regexp"
	"text/template"

	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
)

//go:generate go run github.com/99designs/gqlgen

type Resolver struct{}

var (
	trackerNameRE   = regexp.MustCompile(`^[A-Za-z0-9._-]+$`)
	newTicketTemplate = template.Must(template.New("new-ticket").Parse(`{{.Body}}

-- 
View on the web: {{.Root}}{{.TicketURL}}`))
	ticketStatusTemplate = template.Must(template.New("ticket-status").Parse(`{{if eq .Status "RESOLVED"}}Ticket resolved: {{.Resolution}}{{end}}

-- 
View on the web: {{.Root}}{{.TicketURL}}#event-{{.EventID}}`))
)

type NewTicketDetails struct {
	Body      *string
	Root      string
	TicketURL string
}

type TicketStatusDetails struct {
	Root       string
	TicketURL  string
	EventID    int
	Status     string
	Resolution string
}

func aclBits(input model.ACLInput) uint {
		var bits uint
		if input.Browse {
			bits |= model.ACCESS_BROWSE
		}
		if input.Submit {
			bits |= model.ACCESS_SUBMIT
		}
		if input.Comment {
			bits |= model.ACCESS_COMMENT
		}
		if input.Edit {
			bits |= model.ACCESS_EDIT
		}
		if input.Triage {
			bits |= model.ACCESS_TRIAGE
		}
		return bits
}
