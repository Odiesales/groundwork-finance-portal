from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
AR_SNAPSHOT_DIR = SNAPSHOT_DIR / "ar"
REVENUE_SNAPSHOT_DIR = SNAPSHOT_DIR / "revenue"
ASSETS_DIR = BASE_DIR / "assets"

CURRENT_AR_PATH = EXPORT_DIR / "current_ar_clean.csv"
CURRENT_REVENUE_PATH = EXPORT_DIR / "current_revenue_clean.csv"
REVENUE_HISTORY_PATH = EXPORT_DIR / "revenue_history.csv"

for folder in [UPLOAD_DIR, EXPORT_DIR, AR_SNAPSHOT_DIR, REVENUE_SNAPSHOT_DIR, ASSETS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)
