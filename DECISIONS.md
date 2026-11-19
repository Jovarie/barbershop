# Design decisions

| Date | Decision | Alternatives | Why |
| --- | --- | --- | --- |
| 19 Nov 2026 | Flask with app factory and blueprints | Django, single app.py | Taught in labs; factory makes testing easy |
| 19 Nov 2026 | Neon Postgres for bookings, users, services | Google Cloud SQL, MySQL | Free tier, no card; ACID transactions and constraints stop double booking |
| 19 Nov 2026 | Unique constraint on (barber_id, starts_at) | Check in Python code only | Database enforces it even if two requests arrive at once |
| 19 Nov 2026 | Switched psycopg2 to psycopg 3 | Pin old SQLAlchemy | SQLAlchemy 2.1 defaults to psycopg 3 |
| 19 Nov 2026 | MongoDB Atlas (Paris) for reviews, photos, logs | Firestore | Free 512 MB, flexible documents; EU region for UK GDPR |
| 19 Nov 2026 | certifi for MongoDB TLS certificates | Rely on system certificates | macOS Python lacked CA certs; certifi works the same locally and in the cloud |
