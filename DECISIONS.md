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
