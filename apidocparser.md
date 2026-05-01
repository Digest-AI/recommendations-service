# Parser Service — API Documentation

A Django REST Framework service that scrapes event data from Moldovan event websites (afisha.md, iticket.md, cineplex.md) and exposes the unified data through a read-only REST API.

**Base URL:** `http://localhost:8000`
**API prefix:** `/api/`
**Interactive docs:** `http://localhost:8000/schema/swagger-ui/` | `http://localhost:8000/schema/redoc/`

---

## Response format

Response bodies use **camelCase** JSON keys (converted automatically by the renderer). Query parameter names in URLs are **snake_case** (`date_from`, `price_min`, `page_size`). Dates and times use ISO 8601 (UTC).

### Paginated list response

```json
{
  "count": 342,
  "next": "http://localhost:8000/api/events/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

### Error response

```json
{
  "code": 400,
  "detail": "Invalid date format. Use YYYY-MM-DD.",
  "attr": null
}
```

---

## Internationalization

Multilingual fields are stored explicitly on the record. Each event carries Russian and Romanian variants; there is no English variant.

| Field | Language |
|---|---|
| `titleRu` / `descriptionRu` | Russian |
| `titleRo` / `descriptionRo` | Romanian |

Categories also expose `nameRu` / `nameRo`. Supported `Accept-Language` values: `en`, `ru`, `ro`.

---

## Data model

### Provider (source)

Returned as an object on every event:

```json
{ "id": 1, "slug": "afisha_md", "name": "Afisha.md", "url": "https://afisha.md" }
```

Known slugs: `afisha_md`, `iticket_md`, `cineplex_md`. Additional providers can exist if seeded.

### Category

Each event has zero or more categories (many-to-many):

```json
{ "id": 3, "slug": "concert", "nameRu": "Концерт", "nameRo": "Concert" }
```

Category records are created on the fly by scrapers — the available slugs depend on scraped data. Common slugs include `concert`, `theatre`, `movie`, `sport`, `party`, `kids`, `exhibition`, `festival`, `other`.

---

## Endpoints

### Events

#### `GET /api/events/` — List events

Returns a paginated list of active events. Default page size: 20, maximum: 100.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `category` | string | Filter by category slug. Repeat the parameter or pass a comma-separated list to match any of several categories. |
| `provider` | string | Filter by provider slug. `source` is accepted as a legacy alias. |
| `city` | string | Filter by city — partial, case-insensitive match. |
| `place` | string | Filter by place (venue) name — partial, case-insensitive. `venue` is accepted as a legacy alias. |
| `date_from` | date | Events starting on or after this date (`YYYY-MM-DD`). |
| `date_to` | date | Events starting on or before this date (`YYYY-MM-DD`). |
| `price_min` | number | Minimum `price_from` in MDL (inclusive). |
| `price_max` | number | Maximum `price_from` in MDL (inclusive). |
| `q` | string | Full-text search across `title_ru`, `title_ro`, `description_ru`, `description_ro`, and `place`. |
| `search` | string | DRF `SearchFilter` — same target fields as `q`. |
| `ordering` | string | Sort field: `date_start`, `price_from`, `created_at`. Prefix with `-` for descending. Default: `-date_start`. |
| `page` | integer | Page number. |
| `page_size` | integer | Results per page (max 100). |

**Example**

```
GET /api/events/?category=concert&date_from=2026-05-01&date_to=2026-05-31&page_size=10
```

**List item fields** (lightweight serializer)

```json
{
  "id": 1,
  "slug": "jazz-night-2026-05-10",
  "provider": {
    "id": 1,
    "slug": "afisha_md",
    "name": "Afisha.md",
    "url": "https://afisha.md"
  },
  "url": "https://afisha.md/events/123",
  "titleRu": "Джазовый вечер",
  "titleRo": "Seară de jazz",
  "categories": [
    { "id": 3, "slug": "concert", "nameRu": "Концерт", "nameRo": "Concert" }
  ],
  "dateStart": "2026-05-10T19:00:00Z",
  "address": "str. Mitropolit Varlaam 78, Chișinău",
  "place": "Sala cu Orgă",
  "city": "Кишинёв",
  "priceFrom": "150.00",
  "priceTo": "500.00",
  "imageUrl": "https://afisha.md/images/123.jpg"
}
```

---

#### `GET /api/events/{id}/` — Get event details

Returns the full event record.

```json
{
  "id": 1,
  "slug": "jazz-night-2026-05-10",
  "provider": {
    "id": 1,
    "slug": "afisha_md",
    "name": "Afisha.md",
    "url": "https://afisha.md"
  },
  "externalId": "abc-123",
  "url": "https://afisha.md/events/123",
  "titleRu": "Джазовый вечер",
  "titleRo": "Seară de jazz",
  "descriptionRu": "Вечер классического джаза.",
  "descriptionRo": "O seară de jazz clasic.",
  "categories": [
    { "id": 3, "slug": "concert", "nameRu": "Концерт", "nameRo": "Concert" }
  ],
  "dateStart": "2026-05-10T19:00:00Z",
  "dateEnd": "2026-05-10T22:00:00Z",
  "address": "str. Mitropolit Varlaam 78, Chișinău",
  "place": "Sala cu Orgă",
  "city": "Кишинёв",
  "priceFrom": "150.00",
  "priceTo": "500.00",
  "imageUrl": "https://afisha.md/images/123.jpg",
  "ticketsUrl": "https://afisha.md/events/123/buy",
  "createdAt": "2026-04-28T10:00:00Z"
}
```

---

#### `GET /api/events/upcoming/` — Upcoming events

Active events with `date_start >= now`, ordered ascending by date. Accepts all list filters.

#### `GET /api/events/today/` — Today's events

Active events whose `date_start` falls on today's date (server local time).

#### `GET /api/events/this-week/` — This week's events

Active events in the current calendar week (Monday–Sunday).

#### `GET /api/events/by-date/?date=YYYY-MM-DD` — Events on a specific date

Defaults to today when `date` is omitted. Returns `400` with `{"error": "Invalid date format. Use YYYY-MM-DD."}` on a bad date.

#### `GET /api/events/next-7-days/` — Next 7 days (incl. today)

#### `GET /api/events/next-14-days/` — Next 14 days (incl. today)

#### `GET /api/events/next-month/` — Next 30 days (incl. today)

#### `GET /api/events/next-3-months/` — Next 90 days (incl. today)

All of the above accept the same filters as `/api/events/`.

---

### Category shortcuts

#### `GET /api/category/{category_slug}/` — Events by category

Equivalent to `GET /api/events/?category={category_slug}`. Supports all event-list query parameters; additional `category` query params are combined with the URL slug (any-of match).

```
GET /api/category/concert/
GET /api/category/movie/?date_from=2026-05-01
```

---

### City shortcuts

#### `GET /api/city/{city_name}/` — Events by city

Equivalent to `GET /api/events/?city={city_name}` (partial, case-insensitive).

```
GET /api/city/Кишинёв/
GET /api/city/balti/
```

---

### Reference endpoints

#### `GET /api/categories/` — List all categories

```json
{
  "categories": [
    { "id": 3, "slug": "concert", "nameRu": "Концерт", "nameRo": "Concert", "count": 42 },
    { "id": 4, "slug": "theatre", "nameRu": "Театр", "nameRo": "Teatru", "count": 18 }
  ]
}
```

#### `GET /api/cities/` — List all cities

Cities with at least one active event, ordered by event count descending.

```json
{
  "cities": [
    { "name": "Кишинёв", "count": 310 },
    { "name": "Бельцы", "count": 12 }
  ]
}
```

#### `GET /api/sources/` — List all providers

Returns providers under the `providers` key (the URL keeps the legacy `sources` name).

```json
{
  "providers": [
    { "id": 1, "slug": "afisha_md", "name": "Afisha.md", "url": "https://afisha.md", "count": 120 },
    { "id": 2, "slug": "iticket_md", "name": "iTicket.md", "url": "https://iticket.md", "count": 98 },
    { "id": 3, "slug": "cineplex_md", "name": "Cineplex.md", "url": "https://cineplex.md", "count": 54 }
  ]
}
```

---

### Scraping (dev only)

#### `POST /api/events/scrape/` — Trigger a synchronous scrape

Runs the scraper in the request thread. **Do not use in production** — use a Celery task instead.

**Query parameters**

| Parameter | Default | Description |
|---|---|---|
| `source` | `afisha_md` | Provider slug to scrape: `afisha_md`, `iticket_md`, `cineplex_md`. |
| `category` | all | Category slug to limit the scrape (source-specific). |
| `deep` | `false` | When `true`, visits each event page for full description, address, and `date_end`. Much slower, more complete data. |

```
POST /api/events/scrape/?source=iticket_md&category=concert&deep=true
```

**Success**

```json
{ "source": "iticket_md", "created": 14, "updated": 3 }
```

**Errors**

| Status | Cause |
|---|---|
| `503` | Playwright not installed (`ImportError`). |
| `500` | Unexpected scraper error. |

---

## Pagination

| Parameter | Description |
|---|---|
| `page` | Page number (1-based). |
| `page_size` | Results per page (default 20, max 100). |

```json
{
  "count": 342,
  "next": "http://localhost:8000/api/events/?page=3",
  "previous": "http://localhost:8000/api/events/?page=1",
  "results": [...]
}
```

---

## Ordering

The `ordering` parameter is available on all event-list endpoints.

| Value | Description |
|---|---|
| `date_start` / `-date_start` | By start date (default `-date_start`). |
| `price_from` / `-price_from` | By minimum price. |
| `created_at` / `-created_at` | By creation time. |

```
GET /api/events/?ordering=price_from
```

---

## Common usage examples

**All concerts this month**

```
GET /api/events/?category=concert&date_from=2026-05-01&date_to=2026-05-31
```

**Multi-category filter**

```
GET /api/events/?category=concert,party
GET /api/events/?category=concert&category=party
```

**Search "Artiom" across RU/RO titles, descriptions, and place**

```
GET /api/events/?q=Artiom
```

**Movies from Cineplex, next 7 days**

```
GET /api/events/next-7-days/?provider=cineplex_md&category=movie
```

**Events at a specific place**

```
GET /api/events/?place=Sala+cu+Org%C4%83
```

**Events in Bălți under 100 MDL**

```
GET /api/events/?city=balti&price_max=100
```

**Second page of this week's events, 50 per page**

```
GET /api/events/this-week/?page=2&page_size=50
```
