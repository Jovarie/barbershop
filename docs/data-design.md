# Data design

## SQL (Neon Postgres): structured data with relationships

~~~mermaid
erDiagram
    USERS ||--o| BARBERS : "admin has profile"
    USERS ||--o{ APPOINTMENTS : "customer books"
    BARBERS ||--o{ APPOINTMENTS : "takes"
    SERVICES ||--o{ APPOINTMENTS : "booked as"
    BARBERS ||--o{ WORKING_HOURS : "works"
    BARBERS }o--o{ SERVICES : "offers (barber_services)"

    USERS {
        int id PK
        string email UK
        string name
        string password_hash
        string google_id UK
        string role "customer or admin"
    }
    BARBERS {
        int id PK
        int user_id FK, UK
        text bio
    }
    SERVICES {
        int id PK
        string name
        int duration_min
        int price_pence
        bool active
    }
    WORKING_HOURS {
        int id PK
        int barber_id FK
        int weekday "0 = Monday"
        time start_time
        time end_time
    }
    APPOINTMENTS {
        int id PK
        int customer_id FK
        int barber_id FK
        int service_id FK
        datetime starts_at "unique with barber_id"
        datetime ends_at
        string status "booked, completed, cancelled, no_show"
    }
~~~

## NoSQL (MongoDB Atlas): semi-structured and unstructured data

`reviews`: one document per review, with replies nested inside
~~~json
{
  "_id": "ObjectId",
  "appointment_id": 42,
  "customer_id": 7,
  "rating": 5,
  "text": "Best fade I've had",
  "photos": ["https://storage.googleapis.com/barbershop-photos/r42-1.jpg"],
  "admin_reply": {"text": "Thanks, see you next time", "at": "2026-12-02T10:15:00Z"},
  "created_at": "2026-12-01T18:00:00Z"
}
~~~

`customer_preferences`: fields differ per customer
~~~json
{"customer_id": 7, "usual_cut": "Skin fade, 1 on sides", "notes": "Sensitive scalp", "preferred_times": ["Sat morning"]}
~~~

`activity_log`: append-only audit trail
~~~json
{"user_id": 7, "event": "login", "ip": "81.2.69.160", "at": "2026-12-01T09:00:00Z"}
~~~

## Why this split
- Bookings need foreign keys, constraints and transactions, so they go in SQL. The unique constraint on (barber_id, starts_at) blocks double booking.
- Reviews, preferences and logs vary in shape and are read as whole documents, so they go in MongoDB. No schema migration is needed when a field is added.
