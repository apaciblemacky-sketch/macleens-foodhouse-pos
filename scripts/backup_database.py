#!/usr/bin/env python3
"""Safe Macleen's SQLite backup before deployment.

Default destination is OUTSIDE this Git repository:
    ../macleens_backups/

For Render/PostgreSQL DATABASE_URL deployments, this script deliberately does
not pretend a local SQLite copy is a server backup. Use the database provider's
backup/snapshot feature there.
"""
from __future__ import annotations
import os, sqlite3, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "instance" / "foodhouse_pos.db"
BACKUP_DIR = Path(os.environ.get("MACLEENS_BACKUP_DIR") or (ROOT.parent / "macleens_backups")).expanduser().resolve()

def main() -> int:
    database_url = (os.environ.get("DATABASE_URL") or "").strip()
    if database_url and not database_url.lower().startswith("sqlite"):
        print("INFO: DATABASE_URL is not SQLite. No local database copy was made.")
        print("      Use your hosted database provider's snapshot/backup feature before risky migrations.")
        return 0
    source = DEFAULT_DB
    if database_url.lower().startswith("sqlite") and "///" in database_url:
        raw = database_url.split("///", 1)[1]
        source = Path(raw)
        if not source.is_absolute():
            source = (ROOT / source).resolve()
    if not source.exists():
        print(f"INFO: No local SQLite database found at {source}; nothing to back up.")
        return 0
    try:
        BACKUP_DIR.relative_to(ROOT)
        print("ERROR: Backup destination is inside the Git project. Set MACLEENS_BACKUP_DIR to a folder outside the repository.")
        return 1
    except ValueError:
        pass
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = BACKUP_DIR / f"foodhouse_pos-{stamp}.db"
    src = sqlite3.connect(str(source))
    dst = sqlite3.connect(str(destination))
    try:
        with dst:
            src.backup(dst)
        check = dst.execute("PRAGMA integrity_check").fetchone()
        if not check or str(check[0]).lower() != "ok":
            raise RuntimeError(f"integrity_check returned {check}")
    finally:
        src.close(); dst.close()
    print(f" OK : SQLite backup created: {destination}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
