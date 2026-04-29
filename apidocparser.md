# Parser Service — API Documentation

A Django REST Framework service that scrapes event data from Moldovan event websites (afisha.md, iticket.md, cineplex.md) and exposes the unified data through a read-only REST API.

**Base URL:** `http://localhost:8000`  
**API prefix:** `/api/`  
**Interactive docs:** `http://localhost:8000/schema/swagger-ui/` | `http://localhost:8000/schema/redoc/`

---

## Response format

All responses use **camelCase** JSON keys. Dates and times are in ISO 8601 format (UTC).

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

All errors follow the same shape:

```json
{
  "code": 400,
  "detail": "Invalid date format. Use YYYY-MM-DD.",
  "attr": null
}
```

---

## Internationalization

The service stores multilingual fields. Pass the `Accept-Language` header to indicate your preferred language. Supported values: `en`, `ru`, `ro`.

```
Accept-Language: ru
```

The middleware selects the closest supported language; it falls back to `en` if nothing matches. Each event carries three variants of `title` and `description`:

| Field | Language |
|---|---|
| `title` / `description` | English (default) |
| `titleRu` / `descriptionRu` | Russian |
| `titleRo` / `descriptionRo` | Romanian |

---

## Data sources

| Slug | Site |
|---|---|
| `afisha_md` | Afisha.md |
| `iticket_md` | iTicket.md |
| `cineplex_md` | Cineplex.md |
| `mticket_md` | mTicket.md |
| `fest_md` | Fest.md |

---

## Event categories

| Slug | Label |
|---|---|
| `concert` | Концерт |
| `theatre` | Театр |
| `movie` | Кино |
| `sport` | Спорт |
| `party` | Вечеринка |
| `kids` | Для детей |
| `training` | Тренинг |
| `exhibition` | Выставка |
| `festival` | Фестиваль |
| `free` | Бесплатно |
| `other` | Другое |

---

## Endpoints

### Events

#### `GET /api/events/` — List events

Returns a paginated list of active events. Default page size: 20, maximum: 100.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `category` | string | Filter by category slug (see table above) |
| `source` | string | Filter by source slug (see table above) |
| `city` | string | Filter by city — partial, case-insensitive match |
| `venue` | string | Filter by venue name — partial, case-insensitive match |
| `isFree` | boolean | `true` or `false` — filter free/paid events |
| `dateFrom` | date | Events starting on or after this date (`YYYY-MM-DD`) |
| `dateTo` | date | Events starting on or before this date (`YYYY-MM-DD`) |
| `priceMin` | number | Minimum price in MDL (inclusive) |
| `priceMax` | number | Maximum price in MDL (inclusive) |
| `q` | string | Full-text search across title (all languages), description (all languages), and venue name |
| `ordering` | string | Sort field: `dateStart`, `priceFrom`, `createdAt`. Prefix with `-` for descending. Default: `-dateStart` |
| `page` | integer | Page number |
| `pageSize` | integer | Results per page (max 100) |

**Example request**

```
GET /api/events/?category=concert&dateFrom=2026-05-01&dateTo=2026-05-31&pageSize=10
```

**List item fields** (lightweight serializer)

```json
{
  "id": 1,
  "source": "afisha_md",
  "url": "https://afisha.md/events/123",
  "title": "Jazz Night",
  "titleRu": "Джазовый вечер",
  "titleRo": "Seară de jazz",
  "category": "concert",
  "dateStart": "2026-05-10T19:00:00Z",
  "dateRaw": "10 мая 2026, 19:00",
  "venueName": "Sala cu Orgă",
  "city": "Кишинёв",
  "priceFrom": "150.00",
  "priceTo": "500.00",
  "currency": "MDL",
  "isFree": false,
  "imageUrl": "https://afisha.md/images/123.jpg"
}
```

---

#### `GET /api/events/{id}/` — Get event details

Returns the full event record including descriptions, raw categories, ticket links, and timestamps.

**Detail fields** (full serializer)

```json
{
  "id": 1,
  "source": "afisha_md",
  "externalId": "abc-123",
  "url": "https://afisha.md/events/123",
  "title": "Jazz Night",
  "titleRu": "Джазовый вечер",
  "titleRo": "Seară de jazz",
  "description": "An evening of classic jazz.",
  "descriptionRu": "Вечер классического джаза.",
  "descriptionRo": "O seară de jazz clasic.",
  "category": "concert",
  "rawCategories": ["music", "jazz"],
  "dateStart": "2026-05-10T19:00:00Z",
  "dateEnd": "2026-05-10T22:00:00Z",
  "dateRaw": "10 мая 2026, 19:00",
  "venueName": "Sala cu Orgă",
  "venueAddress": "str. Mitropolit Varlaam 78, Chișinău",
  "city": "Кишинёв",
  "priceFrom": "150.00",
  "priceTo": "500.00",
  "currency": "MDL",
  "isFree": false,
  "imageUrl": "https://afisha.md/images/123.jpg",
  "isActive": true,
  "createdAt": "2026-04-28T10:00:00Z",
  "updatedAt": "2026-04-28T12:00:00Z",
  "lastScrapedAt": "2026-04-28T12:00:00Z"
}
```

> `ticketLinks` is intentionally omitted from the serializer for now — it is stored internally as `{"afisha_md": "https://..."}` for cross-source deduplication.

---

#### `GET /api/events/upcoming/` — Upcoming events

Returns all active events with `dateStart >= now`, ordered ascending by date. Accepts all the same filter/search query parameters as the list endpoint.

```
GET /api/events/upcoming/?category=movie
```

---

#### `GET /api/events/today/` — Today's events

Returns all active events where `dateStart` falls on today's date (server timezone: UTC). Accepts all the same filter/search query parameters.

```
GET /api/events/today/
```

---

#### `GET /api/events/this-week/` — This week's events

Returns all active events in the current calendar week (Monday–Sunday). Accepts all the same filter/search query parameters.

```
GET /api/events/this-week/
```

---

#### `GET /api/events/by-date/` — Events on a specific date

Returns all active events on the given date.

**Query parameter**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | date | No | Target date `YYYY-MM-DD`. Defaults to today. |

```
GET /api/events/by-date/?date=2026-06-15
```

**Error response (invalid date)**

```json
{
  "error": "Invalid date format. Use YYYY-MM-DD."
}
```

---

### Category shortcuts

#### `GET /api/category/{category_slug}/` — Events by category

Equivalent to `GET /api/events/?category={category_slug}`. All event list query parameters are supported.

```
GET /api/category/concert/
GET /api/category/movie/?isFree=true
```

---

### City shortcuts

#### `GET /api/city/{city_name}/` — Events by city

Equivalent to `GET /api/events/?city={city_name}`. The match is partial and case-insensitive.

```
GET /api/city/Кишинёв/
GET /api/city/balti/
```

---

### Reference endpoints

#### `GET /api/categories/` — List all categories

Returns all category slugs with their display names and the count of active events in each.

```json
{
  "categories": [
    { "slug": "concert", "label": "Концерт", "count": 42 },
    { "slug": "theatre", "label": "Театр", "count": 18 },
    ...
  ]
}
```

---

#### `GET /api/cities/` — List all cities

Returns all cities that have at least one active event, ordered by event count descending.

```json
{
  "cities": [
    { "name": "Кишинёв", "count": 310 },
    { "name": "Бельцы", "count": 12 }
  ]
}
```

---

#### `GET /api/sources/` — List all sources

Returns all scraped sources with display names and the count of active events from each.

```json
{
  "sources": [
    { "slug": "afisha_md", "label": "Afisha.md", "count": 120 },
    { "slug": "iticket_md", "label": "iTicket.md", "count": 98 },
    { "slug": "cineplex_md", "label": "Cineplex.md", "count": 54 },
    { "slug": "mticket_md", "label": "mTicket.md", "count": 0 },
    { "slug": "fest_md", "label": "Fest.md", "count": 0 }
  ]
}
```

---

### Scraping (dev only)

#### `POST /api/events/scrape/` — Trigger a synchronous scrape

Immediately runs a scraper in the request thread. **Do not use in production** — use a Celery task instead.

**Query parameters**

| Parameter | Default | Description |
|---|---|---|
| `source` | `afisha_md` | Source to scrape: `afisha_md`, `iticket_md`, `cineplex_md` |
| `category` | all | Category slug to limit the scrape (source-specific) |

```
POST /api/events/scrape/?source=iticket_md&category=concert
```

**Success response**

```json
{
  "source": "iticket_md",
  "created": 14,
  "updated": 3
}
```

**Error responses**

| Status | Cause |
|---|---|
| `503` | Playwright not installed (`ImportError`) |
| `500` | Unexpected scraper error |

---

## Pagination

All list endpoints are paginated.

| Parameter | Description |
|---|---|
| `page` | Page number (1-based) |
| `pageSize` | Results per page (default 20, max 100) |

Response envelope:

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

The `ordering` parameter is available on all event list endpoints. Supported fields:

| Value | Description |
|---|---|
| `dateStart` | Date ascending |
| `-dateStart` | Date descending (default) |
| `priceFrom` | Price ascending |
| `-priceFrom` | Price descending |
| `createdAt` | Creation time ascending |
| `-createdAt` | Creation time descending |

```
GET /api/events/?ordering=priceFrom
```

---

## Common usage examples

**All free concerts this month**

```
GET /api/events/?category=concert&isFree=true&dateFrom=2026-05-01&dateTo=2026-05-31
```

**Search for "Artiom" across all languages**

```
GET /api/events/?q=Artiom
```

**Movies from Cineplex, next 7 days**

```
GET /api/events/upcoming/?source=cineplex_md&category=movie&dateTo=2026-05-05
```

**All events at a specific venue**

```
GET /api/events/?venue=Sala+cu+Org%C4%83
```

**Events in Bălți under 100 MDL**

```
GET /api/events/?city=balti&priceMax=100
```

**Second page of this week's events, 50 per page**

```
GET /api/events/this-week/?page=2&pageSize=50
```
