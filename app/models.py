"""SQL models stored in Neon Postgres."""
from datetime import datetime, timezone

from app.extensions import db

# Many-to-many: which services each barber offers.
barber_services = db.Table(
    "barber_services",
    db.Column("barber_id", db.ForeignKey("barbers.id"), primary_key=True),
    db.Column("service_id", db.ForeignKey("services.id"), primary_key=True),
)


class User(db.Model):
    """A customer or the admin (the barber)."""
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255))   # empty for Google-only accounts
    google_id = db.Column(db.String(255), unique=True)
    role = db.Column(db.String(20), nullable=False, default="customer")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Barber(db.Model):
    """The barber's public profile, linked to their admin account."""
    __tablename__ = "barbers"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("users.id"), unique=True, nullable=False)
    bio = db.Column(db.Text)
    services = db.relationship("Service", secondary=barber_services)


class Service(db.Model):
    """A haircut or treatment. Price in pence to avoid rounding errors."""
    __tablename__ = "services"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration_min = db.Column(db.Integer, nullable=False)
    price_pence = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, default=True)


class WorkingHours(db.Model):
    """When the barber works on a given weekday (0 = Monday)."""
    __tablename__ = "working_hours"
    __table_args__ = (db.UniqueConstraint("barber_id", "weekday"),)
    id = db.Column(db.Integer, primary_key=True)
    barber_id = db.Column(db.ForeignKey("barbers.id"), nullable=False)
    weekday = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)


class Appointment(db.Model):
    """A booking. The unique constraint stops double booking at database level."""
    __tablename__ = "appointments"
    __table_args__ = (
        db.UniqueConstraint("barber_id", "starts_at", name="no_double_booking"),
        db.CheckConstraint("ends_at > starts_at", name="ends_after_start"),
    )
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.ForeignKey("users.id"), nullable=False)
    barber_id = db.Column(db.ForeignKey("barbers.id"), nullable=False)
    service_id = db.Column(db.ForeignKey("services.id"), nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="booked")
    customer = db.relationship("User")
    service = db.relationship("Service")
