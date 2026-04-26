from app.config import ensure_runtime_dirs, settings
from app.database import SessionLocal
from app.services.knowledge import upsert_sample_data


def main() -> None:
    ensure_runtime_dirs()
    db = SessionLocal()
    try:
        upsert_sample_data(db, settings.sample_data_dir)
        print("Sample scenic data imported.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
