# Crown Barbers

An online booking system for an Afro-Caribbean barbershop that specialises in Afro hair and welcomes all hair types. Customers sign in with Google, pick a service and a free time, and manage their bookings. The barber signs in as the admin to see every booking, cancel them, edit services and prices, and set opening hours.

**Live site:** https://crown-barbers-71641.nw.r.appspot.com

Built for the Systems Development unit with Python and Flask, deployed on Google Cloud.

## Features

- Browse services and book a free slot; double booking is blocked by the database
- Google sign-in (Firebase Authentication) with customer and admin roles
- My bookings: see upcoming and past bookings, cancel up to 2 hours before
- Reviews with star ratings on past bookings, and an average rating on the home page
- Admin dashboard: all upcoming bookings, cancellations, recent activity log, services and opening hours
- REST API at `/api/v1` (see [docs/api.md](docs/api.md))
- Confirmation, cancellation and next-day reminder emails, sent by two cloud functions through the Brevo email API

## Architecture

| Part | Technology | Why |
| --- | --- | --- |
| Web app | Flask (app factory and blueprints), Jinja templates, Bootstrap 5 | Taught in the labs; small and explicit |
| Hosting | Google App Engine standard, Python 3.12, London (europe-west2) | Managed platform with HTTPS and scaling built in |
| SQL database | Neon (serverless Postgres) via SQLAlchemy | Bookings need transactions, foreign keys and a no-double-booking rule |
| NoSQL database | MongoDB Atlas via PyMongo | Reviews and the activity log are flexible documents |
| Authentication | Firebase Authentication (Google sign-in) | No passwords stored; tokens verified on the server |
| Cloud functions | Cloud Run functions `booking-email` and `send-reminders` | Email and scheduled work run outside the web app |
| Scheduler | Cloud Scheduler, 18:00 UK time daily | Triggers the reminder emails |
| Email API | Brevo transactional email API | Free tier, no domain needed |
| CI | GitHub Actions runs the tests on every push and pull request | Catches breakages before merging |

Every choice, with the alternatives considered, is in [DECISIONS.md](DECISIONS.md). The data design is in [docs/data-design.md](docs/data-design.md).

## Project layout

```
app/            Flask app: one folder (blueprint) per area
  admin/        barber-only pages
  api/          REST API v1
  auth/         Google sign-in, session cookie, CSRF, role checks
  booking/      services, free slots, booking and cancelling
  reviews/      reviews stored in MongoDB
  templates/    Jinja pages
  notify.py     calls the email cloud function
functions/      the two cloud functions, deployed separately
tests/          pytest tests (Firebase and MongoDB are faked)
app.yaml        App Engine settings
make_secrets.py builds the git-ignored secret files from .env
```

## Run it locally

Needs Python 3.12 and a `.env` file (never committed) with these keys:

```
DATABASE_URL, MONGODB_URI, SECRET_KEY,
FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID, FIREBASE_APP_ID,
ADMIN_EMAILS, COOKIE_SECURE=false,
BREVO_API_KEY, SENDER_EMAIL, FUNCTION_SECRET, EMAIL_FUNCTION_URL
```

and the Firebase service account key saved as `serviceAccountKey.json` (also never committed).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app run init-db
python seed.py
python -m flask --app run run --debug --port 5001
```

Open http://localhost:5001. (Port 5001 because macOS uses 5000 for AirPlay.)

## Tests

```bash
python -m pytest --cov=app
```

The tests use an in-memory SQLite database, a fake Firebase and mongomock, so they need no internet or secrets. GitHub Actions runs them on every push.

## Security

- Google sign-in only: the app stores no passwords
- The Firebase ID token is verified on the server and swapped for an HttpOnly, Secure session cookie
- CSRF token on every form and API write
- Admin role checked on every admin page and API call
- Secrets live in `.env` and generated files that git ignores; no key file is uploaded to production
- HTTPS only on the live site
- Cloud functions reject any request without the shared secret header

## Deployment

See [DEPLOY.md](DEPLOY.md).
