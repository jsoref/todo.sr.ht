package graph

import (
	"regexp"

	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
)

//go:generate go run github.com/99designs/gqlgen

type Resolver struct{}

var (
	trackerNameRE   = regexp.MustCompile(`^[A-Za-z0-9._-]+$`)
)

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
