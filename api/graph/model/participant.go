package model

import "fmt"

// Used internally
type Participant struct {
	ID          int
	Type        string
	UserID      *int
	Mailbox     *string
	Name        *string
	ExternalID  *string
	ExternalURL *string
}

type EmailAddress struct {
	Mailbox string  `json:"mailbox"`
	Name    *string `json:"name"`
}

func (EmailAddress) IsEntity() {}

func (e EmailAddress) CanonicalName() string {
	if e.Name != nil {
		return fmt.Sprintf("%s <%s>", e.Name, e.Mailbox)
	}
	return e.Mailbox
}

type ExternalUser struct {
	ExternalID  string  `json:"externalId"`
	ExternalURL *string `json:"externalUrl"`
}

func (ExternalUser) IsEntity() {}

func (e ExternalUser) CanonicalName() string {
	return e.ExternalID
}
