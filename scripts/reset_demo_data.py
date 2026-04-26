import argparse
from pathlib import Path

from app.config import ensure_runtime_dirs, settings
from app.database import Base, SessionLocal, engine
from app.models import AdminUser, QALog
from app.services.knowledge import import_docx_document, import_xlsx_rows, upsert_sample_data


def reset_logs_only() -> None:
    db = SessionLocal()
    try:
        deleted = db.query(QALog).delete()
        db.commit()
        print(f"Deleted {deleted} QA log records.")
    finally:
        db.close()


def clear_generated_audio() -> None:
    removed = 0
    for file_path in settings.audio_output_dir.glob("*"):
        if file_path.is_file():
            file_path.unlink(missing_ok=True)
            removed += 1
    print(f"Removed {removed} generated audio files.")


def rebuild_all_data() -> None:
    db = SessionLocal()
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db.add(
            AdminUser(
                username=settings.admin_username,
                password=settings.admin_password,
                display_name="系统管理员",
            )
        )
        db.commit()
        upsert_sample_data(db, settings.sample_data_dir)
        materials_dir = Path(settings.official_materials_dir)
        if materials_dir.exists():
            for file_path in materials_dir.rglob("*"):
                if file_path.suffix.lower() == ".docx":
                    import_docx_document(db, file_path, source="official")
                elif file_path.suffix.lower() == ".xlsx":
                    import_xlsx_rows(db, file_path, source="official")
        print("Rebuilt database, sample data, and official materials.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset demo data for Scenic AI backend.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Drop and recreate the whole database, then re-seed admin, sample data, and official materials.",
    )
    args = parser.parse_args()

    ensure_runtime_dirs()
    clear_generated_audio()
    if args.full:
        rebuild_all_data()
    else:
        reset_logs_only()


if __name__ == "__main__":
    main()
