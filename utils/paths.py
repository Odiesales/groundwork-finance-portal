from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DATABASE_DIR = DATA_DIR / "database"
EXPORT_DIR = DATA_DIR / "exports"
ASSETS_DIR = BASE_DIR / "assets"

for folder in [UPLOAD_DIR, DATABASE_DIR, EXPORT_DIR, ASSETS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)
