"""Load starter data into the database. Safe to run more than once."""
from datetime import time

from app import create_app
from app.extensions import db
from app.models import Barber, Service, User, WorkingHours

app = create_app()

with app.app_context():
    if User.query.filter_by(email="barber@barbershop.test").first():
        print("Starter data already loaded")
    else:
        admin = User(email="barber@barbershop.test", name="Shop Barber", role="admin")
        db.session.add(admin)
        db.session.flush()

        services = [
            Service(name="Haircut", duration_min=30, price_pence=1800),
            Service(name="Skin fade", duration_min=45, price_pence=2200),
            Service(name="Beard trim", duration_min=15, price_pence=1000),
        ]
        barber = Barber(user_id=admin.id, bio="Owner and head barber", services=services)
        db.session.add(barber)
        db.session.flush()

        # Tuesday to Saturday, 9am to 5pm (0 = Monday).
        for weekday in range(1, 6):
            db.session.add(WorkingHours(barber_id=barber.id, weekday=weekday,
                                        start_time=time(9, 0), end_time=time(17, 0)))
        db.session.commit()
        print("Starter data loaded")
