from pathlib import Path
import sys

from app.config import ensure_runtime_dirs, settings
from app.database import SessionLocal
from app.services.knowledge import import_docx_document, import_xlsx_rows


def main() -> None:
    ensure_runtime_dirs()
    materials_dir = Path(settings.official_materials_dir)
    if not materials_dir.exists():
        print(f"Official materials directory not found: {materials_dir}")
        return

    db = SessionLocal()
    try:
        for file_path in materials_dir.rglob("*"):
            if file_path.suffix.lower() == ".docx":
                count = import_docx_document(db, file_path, source="official")
                sys.stdout.buffer.write(f"Imported DOCX {file_path.name}: {count} chunks\n".encode("utf-8", "ignore"))
            elif file_path.suffix.lower() == ".xlsx":
                count = import_xlsx_rows(db, file_path, source="official")
                sys.stdout.buffer.write(f"Imported XLSX {file_path.name}: {count} rows\n".encode("utf-8", "ignore"))
    finally:
        db.close()


if __name__ == "__main__":
    main()
