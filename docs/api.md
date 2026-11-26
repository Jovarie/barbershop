# Crown Barbers REST API (v1)

Base URL: `/api/v1`. Every response is JSON. Errors look like `{"error": "message"}` with a matching HTTP status code.

## Authentication

- **Public:** services, free times and reviews need no login.
- **Bookings:** these use the same session cookie as the website, which you get by logging in with Google at `/login`. Without it you get `401`.
- **Changes** (`POST`, `DELETE`) must also send the CSRF token from `GET /api/v1/csrf` in an `X-CSRF-Token` header. Without it you get `403`. This stops other websites making bookings on a logged-in user's behalf.

## Endpoints

| Method | Path | Login | What it does | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| GET | `/csrf` | No | Get a CSRF token | 200 | |
| GET | `/services` | No | List bookable services | 200 | |
| GET | `/services/{id}/slots?date=YYYY-MM-DD` | No | Free start times that day | 200 | 400 bad date, 404 unknown service |
| GET | `/reviews?limit=10` | No | Latest reviews and average rating (MongoDB) | 200 | 400 bad limit |
| GET | `/bookings` | Yes | My bookings, newest first | 200 | 401 |
| GET | `/bookings/{id}` | Yes | One of my bookings | 200 | 401, 404 |
| POST | `/bookings` | Yes + CSRF | Book a time | 201 + `Location` header | 400 bad body, 401, 403, 409 time taken |
| DELETE | `/bookings/{id}` | Yes + CSRF | Cancel (kept as `cancelled`) | 200 | 401, 403, 404, 409 too late |

A booking that isn't yours gets `404`, the same as one that doesn't exist, so nobody can find out which booking ids exist.

## Examples

Public endpoints, from the terminal:

```bash
curl http://localhost:5001/api/v1/services
curl "http://localhost:5001/api/v1/services/1/slots?date=2026-12-01"
curl http://localhost:5001/api/v1/reviews
```

Example response from `/services`:

```json
{"services": [{"id": 3, "name": "Beard trim", "duration_min": 15, "price_pence": 1000,
               "slots_url": "/api/v1/services/3/slots"}]}
```

Logged-in endpoints are easiest to try from the browser. Log in, press **Cmd+Option+J** in Chrome (or Cmd+Option+C in Safari) to open the console, and paste:

```js
const { csrfToken } = await (await fetch("/api/v1/csrf")).json();

// Book (pick a free time from the slots endpoint first)
const made = await fetch("/api/v1/bookings", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
  body: JSON.stringify({ service_id: 1, starts_at: "2026-12-01T10:00:00" })
});
console.log(made.status, await made.json());   // 201 {...}

// List mine
console.log(await (await fetch("/api/v1/bookings")).json());

// Cancel it
const { id } = await (await fetch(made.headers.get("Location"))).json();
const gone = await fetch(`/api/v1/bookings/${id}`,
  { method: "DELETE", headers: { "X-CSRF-Token": csrfToken } });
console.log(gone.status, await gone.json());    // 200 {"status": "cancelled", ...}
```

## Design notes

- **Versioned path** (`/api/v1`), so a future v2 can change things without breaking v1 clients.
- **Status codes carry the meaning:** 201 for created, 409 for a clash, 401 for not logged in, 403 for a missing CSRF token.
- **One set of rules:** the API and the website call the same `make_booking` and `cancel_booking` functions, so the double-booking and 2-hour rules can't drift apart.
