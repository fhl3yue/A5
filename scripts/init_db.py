from app.config import ensure_runtime_dirs, settings
from app.database import Base, SessionLocal, engine
from app.models import AdminUser


def main() -> None:
    ensure_runtime_dirs()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter_by(username=settings.admin_username).first()
        if user is None:
            db.add(
                AdminUser(
                    username=settings.admin_username,
                    password=settings.admin_password,
                    display_name="系统管理员",
                )
            )
            db.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
