package model

import (
	"fmt"
	"io"
	"strconv"
)

type TicketStatus string

const (
	TicketStatusReported   TicketStatus = "REPORTED"
	TicketStatusConfirmed  TicketStatus = "CONFIRMED"
	TicketStatusInProgress TicketStatus = "IN_PROGRESS"
	TicketStatusPending    TicketStatus = "PENDING"
	TicketStatusResolved   TicketStatus = "RESOLVED"
)

var AllTicketStatus = []TicketStatus{
	TicketStatusReported,
	TicketStatusConfirmed,
	TicketStatusInProgress,
	TicketStatusPending,
	TicketStatusResolved,
}

func (e TicketStatus) IsValid() bool {
	switch e {
	case TicketStatusReported, TicketStatusConfirmed, TicketStatusInProgress, TicketStatusPending, TicketStatusResolved:
		return true
	}
	return false
}

func (e TicketStatus) String() string {
	return string(e)
}

func (e *TicketStatus) UnmarshalGQL(v interface{}) error {
	str, ok := v.(string)
	if !ok {
		return fmt.Errorf("enums must be strings")
	}

	*e = TicketStatus(str)
	if !e.IsValid() {
		return fmt.Errorf("%s is not a valid TicketStatus", str)
	}
	return nil
}

func (e TicketStatus) MarshalGQL(w io.Writer) {
	fmt.Fprint(w, strconv.Quote(e.String()))
}

const (
	STATUS_REPORTED    = 0
	STATUS_CONFIRMED   = 1
	STATUS_IN_PROGRESS = 2
	STATUS_PENDING     = 4
	STATUS_RESOLVED    = 8
)

// Creates a TicketStatus from its database representation
func TicketStatusFromInt(status int) TicketStatus {
	switch status {
	case STATUS_REPORTED:
		return TicketStatusReported
	case STATUS_CONFIRMED:
		return TicketStatusConfirmed
	case STATUS_IN_PROGRESS:
		return TicketStatusInProgress
	case STATUS_PENDING:
		return TicketStatusPending
	case STATUS_RESOLVED:
		return TicketStatusResolved
	default:
		panic("database invariant broken")
	}
}

// Converts a TicketStatus to its database representation
func (status TicketStatus) ToInt() int {
	switch status {
	case TicketStatusReported:
		return STATUS_REPORTED
	case TicketStatusConfirmed:
		return STATUS_CONFIRMED
	case TicketStatusInProgress:
		return STATUS_IN_PROGRESS
	case TicketStatusPending:
		return STATUS_PENDING
	case TicketStatusResolved:
		return STATUS_RESOLVED
	default:
		panic("Invalid ticket status")
	}
}

type TicketResolution string

const (
	TicketResolutionUnresolved  TicketResolution = "UNRESOLVED"
	TicketResolutionFixed       TicketResolution = "FIXED"
	TicketResolutionImplemented TicketResolution = "IMPLEMENTED"
	TicketResolutionWontFix     TicketResolution = "WONT_FIX"
	TicketResolutionByDesign    TicketResolution = "BY_DESIGN"
	TicketResolutionInvalid     TicketResolution = "INVALID"
	TicketResolutionDuplicate   TicketResolution = "DUPLICATE"
	TicketResolutionNotOurBug   TicketResolution = "NOT_OUR_BUG"
)

var AllTicketResolution = []TicketResolution{
	TicketResolutionUnresolved,
	TicketResolutionFixed,
	TicketResolutionImplemented,
	TicketResolutionWontFix,
	TicketResolutionByDesign,
	TicketResolutionInvalid,
	TicketResolutionDuplicate,
	TicketResolutionNotOurBug,
}

func (e TicketResolution) IsValid() bool {
	switch e {
	case TicketResolutionUnresolved, TicketResolutionFixed, TicketResolutionImplemented, TicketResolutionWontFix, TicketResolutionByDesign, TicketResolutionInvalid, TicketResolutionDuplicate, TicketResolutionNotOurBug:
		return true
	}
	return false
}

func (e TicketResolution) String() string {
	return string(e)
}

func (e *TicketResolution) UnmarshalGQL(v interface{}) error {
	str, ok := v.(string)
	if !ok {
		return fmt.Errorf("enums must be strings")
	}

	*e = TicketResolution(str)
	if !e.IsValid() {
		return fmt.Errorf("%s is not a valid TicketResolution", str)
	}
	return nil
}

func (e TicketResolution) MarshalGQL(w io.Writer) {
	fmt.Fprint(w, strconv.Quote(e.String()))
}

const (
	RESOLVED_UNRESOLVED  = 0
	RESOLVED_FIXED       = 1
	RESOLVED_IMPLEMENTED = 2
	RESOLVED_WONT_FIX    = 4
	RESOLVED_BY_DESIGN   = 8
	RESOLVED_INVALID     = 16
	RESOLVED_DUPLICATE   = 32
	RESOLVED_NOT_OUR_BUG = 64
)

// Creates a TicketResolution from its database representation
func TicketResolutionFromInt(resolution int) TicketResolution {
	switch resolution {
	case RESOLVED_UNRESOLVED:
		return TicketResolutionUnresolved
	case RESOLVED_FIXED:
		return TicketResolutionFixed
	case RESOLVED_IMPLEMENTED:
		return TicketResolutionImplemented
	case RESOLVED_WONT_FIX:
		return TicketResolutionWontFix
	case RESOLVED_BY_DESIGN:
		return TicketResolutionByDesign
	case RESOLVED_INVALID:
		return TicketResolutionInvalid
	case RESOLVED_DUPLICATE:
		return TicketResolutionDuplicate
	case RESOLVED_NOT_OUR_BUG:
		return TicketResolutionNotOurBug
	default:
		panic("database invariant broken")
	}
}

// Converts a TicketResolution to its database representation
func (e TicketResolution) ToInt() int {
	switch e {
	case TicketResolutionUnresolved:
		return RESOLVED_UNRESOLVED
	case TicketResolutionFixed:
		return RESOLVED_FIXED
	case TicketResolutionImplemented:
		return RESOLVED_IMPLEMENTED
	case TicketResolutionWontFix:
		return RESOLVED_WONT_FIX
	case TicketResolutionByDesign:
		return RESOLVED_BY_DESIGN
	case TicketResolutionInvalid:
		return RESOLVED_INVALID
	case TicketResolutionDuplicate:
		return RESOLVED_DUPLICATE
	case TicketResolutionNotOurBug:
		return RESOLVED_NOT_OUR_BUG
	default:
		panic("Invalid TicketResolution")
	}
}
