# Design decisions

| Date | Decision | Alternatives | Why |
| --- | --- | --- | --- |
| 19 Nov 2026 | Flask with app factory and blueprints | Django, single app.py | Taught in labs; factory makes testing easy |
| 19 Nov 2026 | Neon Postgres for bookings, users, services | Google Cloud SQL, MySQL | Free tier, no card; ACID transactions and constraints stop double booking |
| 19 Nov 2026 | Unique constraint on (barber_id, starts_at) | Check in Python code only | Database enforces it even if two requests arrive at once |
| 19 Nov 2026 | Switched psycopg2 to psycopg 3 | Pin old SQLAlchemy | SQLAlchemy 2.1 defaults to psycopg 3 |
| 19 Nov 2026 | MongoDB Atlas (Paris) for reviews, photos, logs | Firestore | Free 512 MB, flexible documents; EU region for UK GDPR |
| 19 Nov 2026 | certifi for MongoDB TLS certificates | Rely on system certificates | macOS Python lacked CA certs; certifi works the same locally and in the cloud |
| 25 Nov 2026 | Slot logic as a pure function in slots.py | Query logic inside the route | Testable without a database; 4 unit tests cover hours, overlaps and past times |
| 25 Nov 2026 | Check slot is free in code AND rely on DB unique constraint | Code check only | Defence in depth: the constraint still blocks a double booking if two requests arrive together |
| 25 Nov 2026 | "My bookings" page waits for login | Look up bookings by email | Lookup by email would let anyone see another customer's bookings |
| 25 Nov 2026 | Bootstrap 5 from a CDN plus one custom style.css | Tailwind, hand-written CSS | Responsive layout and accessible forms for free, so time went on the brand (Afro-Caribbean palette, Bebas Neue headings); Tailwind needs a Node build step |
| 25 Nov 2026 | Firebase Authentication with Google Sign-In | Own email/password login with salted hashes | Google handles passwords, 2FA and recovery, so I store no passwords; taught in lab 6 |
| 25 Nov 2026 | Swap the ID token for an HttpOnly Firebase session cookie | Keep the token in browser storage | JavaScript can't read an HttpOnly cookie, so an XSS bug can't steal the login; sign-ins older than 5 minutes can't become a new 5-day session |
| 25 Nov 2026 | CSRF token on every POST, checked in one before_request hook | Add a check to each form | Stops other sites submitting bookings or logout as the user; one hook means a new form can't forget it |
| 25 Nov 2026 | Admin = email listed in ADMIN_EMAILS | Admin sign-up page, hard-coded email | No sign-up page to abuse; the barber's email lives in config, not code |
| 25 Nov 2026 | Return 404 for someone else's booking | 403 Forbidden | Doesn't reveal which booking numbers exist |
| 25 Nov 2026 | Fake Firebase in tests | Call real Firebase in tests | Tests run offline and fast with no key file, but still go through the real login route and decorators |
| 25 Nov 2026 | Reviews and activity log in MongoDB, bookings stay in SQL | Everything in Postgres | Bookings need ACID transactions and constraints; reviews and logs are flexible, write-heavy documents with no joins, which suits a document store |
| 25 Nov 2026 | Unique index on reviews.appointment_id | Check in Python only | The database enforces one review per appointment even if two requests arrive together |
| 25 Nov 2026 | Average rating via a MongoDB aggregation pipeline | Load every review and average in Python | The database does the work and only one small result travels over the network |
| 25 Nov 2026 | TTL index deletes activity logs after 90 days | Keep logs forever, or a manual cleanup job | Data minimisation under UK GDPR, with no extra code to run |
| 25 Nov 2026 | Only the first name is stored and shown on reviews | Show the full name | Privacy: reviews are public on the home page |
| 25 Nov 2026 | App keeps working if MongoDB is down | Let errors crash the page | Bookings (SQL) are the core job; reviews and logs are extras, so they fail quietly and are logged |
| 25 Nov 2026 | mongomock for tests | Test against the real Atlas cluster | Fast, offline, and tests can't pollute real data |
| 25 Nov 2026 | REST API under /api/v1 with JSON and proper status codes | GraphQL, or JSON mixed into page routes | REST matches the resources (services, slots, bookings); versioned path lets v2 change without breaking clients |
| 25 Nov 2026 | API reuses the website's session cookie + CSRF header | Separate API keys or JWTs | One login system to secure; the API is used by the site's own pages and the demo; tokens would be the next step for a mobile app |
| 25 Nov 2026 | make_booking() and cancel_booking() shared by web and API | Duplicate logic in each route | Business rules live in one place, so they can't drift apart |
| 25 Nov 2026 | 404 (not 403) for other users' bookings | 403 Forbidden | Doesn't reveal which booking ids exist |
| 25 Nov 2026 | REST API under /api/v1 with JSON and proper status codes | GraphQL, or JSON mixed into page routes | REST matches the resources (services, slots, bookings); versioned path lets v2 change without breaking clients |
| 25 Nov 2026 | API reuses the website's session cookie + CSRF header | Separate API keys or JWTs | One login system to secure; the API is used by the site's own pages and the demo; tokens would be the next step for a mobile app |
| 25 Nov 2026 | make_booking() and cancel_booking() shared by web and API | Duplicate logic in each route | Business rules live in one place, so they can't drift apart |
| 25 Nov 2026 | 404 (not 403) for other users' bookings | 403 Forbidden | Doesn't reveal which booking ids exist |
