import os
import sys
from pathlib import Path


def configure_runtime_base_dir() -> Path:
    if "SCENIC_AI_BASE_DIR" in os.environ:
        return Path(os.environ["SCENIC_AI_BASE_DIR"]).resolve()

    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parents[2]

    os.environ["SCENIC_AI_BASE_DIR"] = str(base_dir)
    return base_dir


def bootstrap_runtime_data() -> None:
    from app.config import ensure_runtime_dirs, settings
    from app.database import Base, SessionLocal, engine
    from app.models import AdminUser
    from app.services.knowledge import upsert_sample_data

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
        upsert_sample_data(db, settings.sample_data_dir)
    finally:
        db.close()


def main() -> None:
    configure_runtime_base_dir()
    bootstrap_runtime_data()

    import uvicorn
    from app.config import settings
    from app.main import app

    print(f"Starting backend on http://127.0.0.1:{settings.app_port}")
    print(f"Frontend: http://127.0.0.1:{settings.app_port}/app/")
    print(f"API docs: http://127.0.0.1:{settings.app_port}/docs")
    uvicorn.run(app, host=settings.app_host, port=settings.app_port, reload=False)


if __name__ == "__main__":
    main()
