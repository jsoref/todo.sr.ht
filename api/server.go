package main

import (
	"context"
	"log"
	"net/http"
	"strconv"

	"git.sr.ht/~sircmpwn/core-go/config"
	"git.sr.ht/~sircmpwn/core-go/server"
	"git.sr.ht/~sircmpwn/core-go/webhooks"
	work "git.sr.ht/~sircmpwn/dowork"
	"github.com/99designs/gqlgen/graphql"
	"github.com/go-chi/chi"

	"git.sr.ht/~sircmpwn/todo.sr.ht/api/account"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/api"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/graph/model"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/loaders"
	"git.sr.ht/~sircmpwn/todo.sr.ht/api/trackers"
)

func main() {
	appConfig := config.LoadConfig(":5103")

	gqlConfig := api.Config{Resolvers: &graph.Resolver{}}
	gqlConfig.Directives.Internal = server.Internal
	gqlConfig.Directives.Private = server.Private
	gqlConfig.Directives.Access = func(ctx context.Context, obj interface{},
		next graphql.Resolver, scope model.AccessScope,
		kind model.AccessKind) (interface{}, error) {
		return server.Access(ctx, obj, next, scope.String(), kind.String())
	}
	schema := api.NewExecutableSchema(gqlConfig)

	scopes := make([]string, len(model.AllAccessScope))
	for i, s := range model.AllAccessScope {
		scopes[i] = s.String()
	}

	accountQueue := work.NewQueue("account")
	trackersQueue := work.NewQueue("trackers")
	webhookQueue := webhooks.NewQueue(schema)
	legacyWebhooks := webhooks.NewLegacyQueue()

	gsrv := server.NewServer("todo.sr.ht", appConfig).
		WithDefaultMiddleware().
		WithMiddleware(
			loaders.Middleware,
			account.Middleware(accountQueue),
			trackers.Middleware(trackersQueue),
			webhooks.Middleware(webhookQueue),
			webhooks.LegacyMiddleware(legacyWebhooks),
		).
		WithSchema(schema, scopes).
		WithQueues(
			accountQueue,
			trackersQueue,
			webhookQueue.Queue,
			legacyWebhooks.Queue,
		)

	gsrv.Router().Get("/query/tracker/{id}.json.gz", func(w http.ResponseWriter, r *http.Request) {
		id, err := strconv.Atoi(chi.URLParam(r, "id"))
		if err != nil {
			w.WriteHeader(http.StatusBadRequest)
			w.Write([]byte("Invalid tracker ID\r\n"))
			return
		}

		w.Header().Set("Content-Type", "application/gzip")
		w.Header().Set("Content-Disposition", `attachment; filename="tracker.json.gz"`)
		if err := trackers.ExportDump(r.Context(), id, w); err != nil {
			log.Printf("Tracker export failed: %v", err)
			w.WriteHeader(http.StatusInternalServerError)
		}
	})

	gsrv.Run()
}
