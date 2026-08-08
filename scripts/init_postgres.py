from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db import import_recipes_csv_to_postgres, init_db, migrate_sqlite_user_data_to_postgres, postgres_configured


def main() -> None:
    if not postgres_configured():
        raise SystemExit(
            "PostgreSQL 未启用。请先设置 TASTEPILOT_USE_POSTGRES=true，并提供 DATABASE_URL / POSTGRES_DSN。"
        )

    init_db()
    migrated = migrate_sqlite_user_data_to_postgres()
    recipe_count = import_recipes_csv_to_postgres()

    print("PostgreSQL 初始化完成。")
    print("已迁移用户数据：")
    for key, value in migrated.items():
        print(f"- {key}: {value}")
    print(f"- recipes: {recipe_count}")


if __name__ == "__main__":
    main()
