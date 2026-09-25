"""Dev seed: centres, tests, offerings, demo user. Never imported by production code paths."""
from decimal import Decimal

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import CentreOffering, DiagnosticCentre, DiagnosticTest, User

CENTRES = [
    ("CityCare Diagnostics", "Indiranagar, Bengaluru"),
    ("Apollo Labs", "Jubilee Hills, Hyderabad"),
]

TESTS = [
    ("Lipid Profile", "Fasting cholesterol panel"),
    ("HbA1c", "3-month blood sugar average"),
    ("Thyroid TSH", "Thyroid stimulating hormone"),
]

PRICES = {
    ("CityCare Diagnostics", "Lipid Profile"): Decimal("499.00"),
    ("CityCare Diagnostics", "HbA1c"): Decimal("349.00"),
    ("Apollo Labs", "Lipid Profile"): Decimal("599.00"),
    ("Apollo Labs", "Thyroid TSH"): Decimal("299.00"),
}


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "demo@eve.health").first() is None:
            db.add(
                User(name="Demo User", email="demo@eve.health", password_hash=hash_password("demo-pass-1"))
            )
        centres: dict[str, DiagnosticCentre] = {}
        for name, loc in CENTRES:
            c = db.query(DiagnosticCentre).filter(DiagnosticCentre.name == name).first()
            if c is None:
                c = DiagnosticCentre(name=name, location=loc)
                db.add(c)
                db.flush()
            centres[name] = c
        tests: dict[str, DiagnosticTest] = {}
        for name, desc in TESTS:
            t = db.query(DiagnosticTest).filter(DiagnosticTest.name == name).first()
            if t is None:
                t = DiagnosticTest(name=name, description=desc)
                db.add(t)
                db.flush()
            tests[name] = t
        for (cname, tname), price in PRICES.items():
            exists = (
                db.query(CentreOffering)
                .filter(
                    CentreOffering.centre_id == centres[cname].id,
                    CentreOffering.test_id == tests[tname].id,
                )
                .first()
            )
            if exists is None:
                db.add(
                    CentreOffering(
                        centre_id=centres[cname].id, test_id=tests[tname].id, price=price
                    )
                )
        db.commit()
        print("Seeded demo data (demo@eve.health / demo-pass-1)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
