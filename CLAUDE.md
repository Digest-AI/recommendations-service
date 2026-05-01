# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django REST Framework service that recommends Moldova events to users. Owns no event data — it consumes events from a separate parser service (5 sources: afisha.md, iticket.md, mticket.md, fest.md, cineplex.md) and ranks them per user. Users live in another service; this service identifies them by an opaque `user_id` string.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Mac/Linux
pip install -r r.txt
cp .env.example .env               # fill in required vars (see below)
python manage.py migrate
python manage.py runserver 8080
```

Required `.env` vars: `SECRET_KEY`, `ENVIRONMENT`, `HOST`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `SERVICE_ID`, `SERVICE_SECRET`.

Optional: `EVENT_GATEWAY` (`in_memory` default — reads `api/gateways/seed_events.json`; set to `http` to call the parser service), `EVENTS_API_BASE_URL` (e.g. `http://localhost:8000`, required when `EVENT_GATEWAY=http`).

## Common Commands

```bash
python manage.py runserver 8080    # dev server
python manage.py migrate           # apply migrations
python manage.py makemigrations    # generate migrations after model changes
python manage.py test              # run all tests
python manage.py test api.tests.TestFoo  # run a single test class
mypy .                             # type check
```

API docs available at `/schema/swagger-ui/` and `/schema/redoc/` in DEBUG mode.

## Architecture

```
core/                       Django project config (settings, root urls, wsgi/asgi)
api/
  dto.py                    EventDTO + EventFilters frozen dataclasses (parser-schema mirror)
  gateways/                 EventGateway protocol + In-memory + Http implementations
  models/                   UserProfile, Interaction, RecommendationLog (local DB)
  recommendations/          ContentScorer, MMR diversity, RecommendationEngine
  serializers/, views/, urls.py    REST endpoints
utils/                      Shared infrastructure (not business logic)
apidocparser.md             Parser service API reference (used by HttpEventGateway)
```

The service has three "layers" worth keeping straight:

1. **Data layer (`api/gateways/`)** — abstracts where events come from. The
   recommender never sees HTTP, JSON, or seed files; it only sees `EventDTO`s
   returned by an `EventGateway`.
2. **Recommendation layer (`api/recommendations/`)** — pure logic: takes a
   user + a candidate list, returns a ranked list. No I/O of its own.
3. **Transport layer (DRF views, serializers, middleware, utils)** — handles
   HTTP, validation, camelCase ↔ snake_case translation, error shaping.

### Recommendation flow (per request)

End-to-end, a `GET /api/recommendations/?userId=...` walks through:

1. **View** (`api/views/recommendations.py`) — validates query params (`userId`, `limit`, `diversity`, `excludeSeen`) using `RecommendationQuerySerializer`, after running `pythonize` on the query dict (DRF parsers don't touch query strings).
2. **`RecommendationEngine.recommend()`** (`api/recommendations/engine.py`) — orchestrates:
   - `UserContext.build(user_id, gateway.get)`:
     - Loads `UserProfile` (or `None` if absent — the request still works for unknown users with degraded personalisation).
     - Pulls the last 200 `Interaction` rows for this user, ordered newest first. Their `event_id`s populate `seen_event_ids`. For each *positive* interaction (`click`, `save`, `ticket_click`) the gateway is asked for the event detail and its venue / source / category go into `Counter`s — these are the user's revealed-preference signals.
   - `EventGateway.list(filters)` — fetches upcoming candidates. Only `starts_after=now` is always set; the profile adds `free_only` when the user opted into free-only.
   - If `excludeSeen=true` (default), seen ids are dropped here.
   - `ContentScorer.score(event, ctx)` runs over each candidate and returns a `ScoredEvent(event, score, breakdown)`.
   - `mmr_rerank(scored, top_k=limit, lambda_=diversity)` picks the final list.
   - Every served recommendation is bulk-inserted into `RecommendationLog` with its full feature breakdown — this is the training set for Phase 2.
3. **Response shaping** — view returns a list of `{rank, score, featureBreakdown, event}`. The `CamelCaseJSONRenderer` flips snake_case keys to camelCase on the way out.

### Scoring (Phase 1, content-based)

`ContentScorer` (`api/recommendations/scoring.py`) computes a linear combination of eight interpretable features, each in `[0, 1]`. Weights live in `ContentScorer.weights` and are intentionally hand-tuned and visible:

| Feature | Weight | Meaning |
|---|---|---|
| `category_match` | 0.30 | 1 if event's category is in `profile.preferred_categories`, else 0 |
| `raw_category_overlap` | 0.20 | Jaccard overlap between event tags and `profile.preferred_raw_categories` |
| `city_match` | 0.10 | 1 if event city == `profile.home_city` |
| `price_fit` | 0.10 | 1 if free or within `max_price`; decays linearly past budget; 0.5 if no budget set |
| `recency` | 0.10 | `exp(-days_until_event / 14)` — soonest events score highest |
| `venue_affinity` | 0.10 | `log1p(visits) / log(5)`, clamped to 1 — repeated venues from past positive interactions |
| `source_affinity` | 0.05 | Share of past positive interactions from this source |
| `category_affinity` | 0.05 | Share of past positive interactions in this category |

Affinities come from `UserContext.build()`. The first four use the `UserProfile`; if the profile is `None` they all return 0 and the user gets a less personalised but still time-ordered list.

The `breakdown` dict that ends up in `RecommendationLog.feature_breakdown` is exactly these eight feature values — so when Phase 2 trains a LightGBM ranker, the input columns already exist in the log table.

### Diversity (MMR re-rank)

`mmr_rerank()` (`api/recommendations/diversity.py`) implements Maximal Marginal Relevance: each pick maximises `λ · score(event) − (1 − λ) · max_similarity_to_already_picked`. Similarity is a simple penalty for sharing category, venue, or source with anything already in the result. `λ = diversity` query param (default 0.7 — score-leaning). At `λ = 1` it degenerates to top-K by score; at `λ = 0` it picks the most diverse candidates regardless of score.

This avoids the "all five recommendations are the same horror movie at the same cinema" failure mode that pure score-sort produces.

### EventGateway abstraction

`api/gateways/base.py` defines a `Protocol` with two methods: `list(filters) -> list[EventDTO]` and `get(event_id) -> EventDTO | None`. The active backend is selected at startup in `api/gateways/__init__.py::get_event_gateway()` via the `EVENT_GATEWAY` setting (memoised — one instance per process).

Two implementations exist:

- **`InMemoryEventGateway`** (`in_memory.py`) — loads `seed_events.json` once at startup. Dates are stored as `date_start_in_days` offsets relative to "now" so seed data never goes stale. Filtering is a linear scan; fine for the dozens of events in seed. Used in dev and tests.
- **`HttpEventGateway`** (`http.py`) — calls the parser service over HTTP. Contract is documented in `apidocparser.md` at the repo root.

#### How `HttpEventGateway` works

- **`list(filters)`** → `GET /api/events/`. `EventFilters` is translated to query params: `starts_after` → `dateFrom` (YYYY-MM-DD), `free_only` → `isFree=true`, `max_price` → `priceMax`, plus `category` / `source` / `city` if set. Always sends `ordering=dateStart` so candidates arrive earliest-first. Paginates up to `max_pages=5 × pageSize=100` (= 500 candidates max per call) and stops early when the parser stops returning a `next` URL.
- **`get(event_id)`** → `GET /api/events/{id}/`. Returns the full record (descriptions, `rawCategories`, venue address). Used by `UserContext.build()` to look up events from past interactions when computing affinity counters.
- **camelCase translation** — parser responses are camelCase JSON; the gateway runs them through `utils.transformers.pythonize` (recursive) before mapping to `EventDTO`. Dates are parsed as ISO 8601 (with `Z` → `+00:00` fixup), prices as `Decimal`.
- **Caching** — both `list` and `get` results are stored in Django's cache (locmem by default). TTLs: 60s for list pages, 300s for detail records. Keys are derived from filter params / event id. This keeps repeated recommendation requests from hammering the parser.
- **Failure mode** — on timeout, network error, 5xx, or invalid JSON the call returns `None` / `[]` and logs a warning at WARNING. The recommender then either has fewer candidates or returns an empty list — it never propagates a 500 from the parser to the caller.

#### Known caveat: list vs detail serializers

The parser's list endpoint uses a lightweight serializer that **omits `descriptionRu/Ro` and `rawCategories`**. That means for candidates fetched via `list()`, the scorer's `_raw_overlap` feature always evaluates to 0. The `get()` path returns the full record, so affinity computation from past interactions is unaffected. If `raw_category_overlap` becomes important to ranking quality, options are: (a) ask the parser to expand its list serializer, (b) batch-fetch detail for top-K candidates after a cheap pre-filter, or (c) move to embedding-based retrieval (Phase 3) which doesn't need raw-category tags.

### Local models

- `UserProfile` (`user_profiles` table) — `user_id` (opaque), `preferred_categories`, `preferred_raw_categories` (free-form tags), `home_city`, `language`, `max_price`, `free_only`.
- `Interaction` (`interactions` table) — `user_id`, `event_id`, `kind` (`view|click|save|ticket_click|dismiss`), `created_at`. Indexed on `(user_id, created_at)` and `(event_id, kind)`.
- `RecommendationLog` (`recommendation_logs` table) — `user_id`, `event_id`, `rank`, `score`, `feature_breakdown` (JSON), `served_at`.

### Endpoints

| Method | Path | Body / Query |
|---|---|---|
| `GET` | `/api/recommendations/` | `userId`, `limit` (1–50), `diversity` (0–1), `excludeSeen` (bool) |
| `POST` | `/api/interactions/` | `{userId, eventId, kind}` |
| `GET` / `PUT` | `/api/profiles/<userId>/` | profile fields (PUT is upsert) |

### Roadmap

- **Phase 1 (current):** content-based scoring with hand-tuned linear weights.
- **Phase 2:** once ~5k logged interactions exist, train a LightGBM ranker on `RecommendationLog.feature_breakdown` joined with `Interaction` (positive label = click within 24h). Same features, learned weights.
- **Phase 3:** two-stage — pgvector ANN retrieval (multilingual sentence-transformer embeddings of titles + descriptions) → LightGBM ranker → MMR.

## Request/response pipeline

1. `utils/i18n_middleware.py` — reads `Accept-Language`, attaches `request.language` (one of `en`, `ru`, `ro`)
2. DRF view handles the request
3. `utils/renderers.py` (`CamelCaseJSONRenderer`) — converts all snake_case keys to camelCase before sending the response
4. `utils/parsers.py` (`CamelCaseJSONParser`) — converts incoming camelCase JSON body to snake_case before DRF sees it (note: query strings bypass the parser; views call `pythonize(request.query_params.dict())` explicitly)
5. `utils/exception_handler.py` — normalizes all errors to `{code, detail, attr}` shape

**Exception classes** (`utils/exceptions/classes.py`): use `BadRequest`, `Unauthorized`, `Forbidden`, `NotFound`, `InternalServerError` (all extend `APIException` which adds an optional `attr` field to DRF's base exception). Never raise raw `DRFAPIException`; always use these subclasses.

**Error response shape:** `{"code": <http_status_int>, "detail": "<string>", "attr": "<field_name_or_null>"}`

## Git Workflow

Branch naming: `feature/`, `fix/`, `docs/`, `chore/`.

Commit messages must be descriptive English sentences — not generic words like `fix`, `init`, `commit`.

Flow: create issue → create branch from issue → code → push → open PR → merge to `main`.
