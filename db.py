from __future__ import annotations

import hashlib
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from secrets import token_urlsafe
from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - optional until postgres is installed locally
    psycopg = None
    dict_row = None


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "tastepilot.db"
RECIPES_CSV_PATH = BASE_DIR / "data" / "recipes.csv"
DEFAULT_PG_DSN = "postgresql://localhost:5432/tastepilot"
RECIPE_COLUMNS = [
    "id",
    "name",
    "cuisine",
    "staple_category",
    "cuisine_group",
    "beverage_category",
    "flavor_tags",
    "scene_tags",
    "diet_tags",
    "feature_tags",
    "budget_level",
    "cook_time_minutes",
    "difficulty",
    "ingredients",
    "is_spicy",
    "is_vegetarian",
    "calorie_level",
    "description",
]


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_pg_dsn() -> str:
    return (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_DSN")
        or os.getenv("POSTGRES_URL")
        or DEFAULT_PG_DSN
    )


def postgres_enabled() -> bool:
    return _env_flag("TASTEPILOT_USE_POSTGRES", False)


def postgres_driver_available() -> bool:
    return psycopg is not None


def postgres_configured() -> bool:
    return postgres_enabled() and postgres_driver_available()


def _sqlite_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


@contextmanager
def get_sqlite_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


@contextmanager
def get_postgres_connection():
    if not postgres_driver_available():
        raise RuntimeError("psycopg 未安装，无法连接 PostgreSQL。")

    connection = psycopg.connect(_get_pg_dsn(), row_factory=dict_row)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def using_postgres() -> bool:
    return postgres_configured()


def init_sqlite_db() -> None:
    with get_sqlite_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                favorite_flavors TEXT,
                disliked_ingredients TEXT,
                diet_goal TEXT,
                budget_level TEXT,
                cooking_time_limit TEXT,
                vegetarian_preference TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS login_sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profile_type TEXT NOT NULL,
                profile_value TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_query_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                flavor_tags TEXT,
                cuisine_groups TEXT,
                scene TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )


def init_postgres_db() -> None:
    if not postgres_configured():
        return

    with get_postgres_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
                nickname TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id BIGINT PRIMARY KEY REFERENCES users(id),
                favorite_flavors TEXT,
                disliked_ingredients TEXT,
                diet_goal TEXT,
                budget_level TEXT,
                cooking_time_limit TEXT,
                vegetarian_preference TEXT,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_actions (
                id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
                user_id BIGINT NOT NULL REFERENCES users(id),
                recipe_id BIGINT NOT NULL,
                action_type TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS login_sessions (
                token TEXT PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id),
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_codes (
                id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
                user_id BIGINT NOT NULL REFERENCES users(id),
                email TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                used_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_feedback (
                id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
                user_id BIGINT NOT NULL REFERENCES users(id),
                profile_type TEXT NOT NULL,
                profile_value TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_query_signals (
                id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
                user_id BIGINT NOT NULL REFERENCES users(id),
                flavor_tags TEXT,
                cuisine_groups TEXT,
                scene TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id BIGINT PRIMARY KEY,
                name TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                staple_category TEXT,
                cuisine_group TEXT,
                beverage_category TEXT,
                flavor_tags TEXT,
                scene_tags TEXT,
                diet_tags TEXT,
                feature_tags TEXT,
                budget_level TEXT,
                cook_time_minutes INTEGER NOT NULL,
                difficulty TEXT,
                ingredients TEXT,
                is_spicy INTEGER,
                is_vegetarian INTEGER,
                calorie_level TEXT,
                description TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_actions_user_id ON user_actions(user_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_query_signals_user_id ON user_query_signals(user_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_profile_feedback_user_id ON profile_feedback(user_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_recipes_cuisine_group ON recipes(cuisine_group)
            """
        )


def init_db() -> None:
    init_sqlite_db()
    init_postgres_db()


def _hash_password(password: str) -> str:
    if len(password) < 6:
        raise ValueError("密码至少需要 6 位。")

    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"{salt.hex()}${derived.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    salt_hex, hash_hex = password_hash.split("$", maxsplit=1)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        120000,
    )
    return derived.hex() == hash_hex


def create_user(nickname: str, email: str, password: str) -> int:
    if not nickname:
        raise ValueError("昵称不能为空。")
    if "@" not in email:
        raise ValueError("请输入有效邮箱。")

    email = email.lower()
    password_hash = _hash_password(password)

    if using_postgres():
        try:
            with get_postgres_connection() as connection:
                row = connection.execute(
                    """
                    INSERT INTO users (nickname, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (nickname, email, password_hash),
                ).fetchone()
                user_id = int(row["id"])
                connection.execute(
                    """
                    INSERT INTO user_preferences (
                        user_id, favorite_flavors, disliked_ingredients, diet_goal,
                        budget_level, cooking_time_limit, vegetarian_preference
                    ) VALUES (%s, '', '', '均衡饮食', '中等预算', '30 分钟内', '不限')
                    """,
                    (user_id,),
                )
                return user_id
        except Exception as exc:
            raise ValueError("这个邮箱已经注册过了。") from exc

    try:
        with get_sqlite_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO users (nickname, email, password_hash) VALUES (?, ?, ?)",
                (nickname, email, password_hash),
            )
            user_id = cursor.lastrowid
            connection.execute(
                """
                INSERT INTO user_preferences (
                    user_id, favorite_flavors, disliked_ingredients, diet_goal,
                    budget_level, cooking_time_limit, vegetarian_preference
                ) VALUES (?, '', '', '均衡饮食', '中等预算', '30 分钟内', '不限')
                """,
                (user_id,),
            )
            return int(user_id)
    except sqlite3.IntegrityError as exc:
        raise ValueError("这个邮箱已经注册过了。") from exc


def authenticate_user(email: str, password: str) -> dict | None:
    email = email.lower()
    if using_postgres():
        with get_postgres_connection() as connection:
            row = connection.execute(
                "SELECT id, nickname, email, password_hash FROM users WHERE email = %s",
                (email,),
            ).fetchone()
        if row is None or not _verify_password(password, row["password_hash"]):
            return None
        return {"id": row["id"], "nickname": row["nickname"], "email": row["email"]}

    with get_sqlite_connection() as connection:
        row = connection.execute(
            "SELECT id, nickname, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    if row is None or not _verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "nickname": row["nickname"], "email": row["email"]}


def get_user_by_email(email: str) -> dict | None:
    email = email.lower()
    if using_postgres():
        with get_postgres_connection() as connection:
            row = connection.execute(
                "SELECT id, nickname, email FROM users WHERE email = %s",
                (email,),
            ).fetchone()
        return {"id": row["id"], "nickname": row["nickname"], "email": row["email"]} if row else None

    with get_sqlite_connection() as connection:
        row = connection.execute(
            "SELECT id, nickname, email FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    return {"id": row["id"], "nickname": row["nickname"], "email": row["email"]} if row else None


def create_login_session(user_id: int, duration_days: int = 30) -> str:
    token = token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=duration_days)

    if using_postgres():
        with get_postgres_connection() as connection:
            connection.execute(
                "INSERT INTO login_sessions (token, user_id, expires_at) VALUES (%s, %s, %s)",
                (token, user_id, expires_at),
            )
        return token

    with get_sqlite_connection() as connection:
        connection.execute(
            "INSERT INTO login_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at.isoformat(timespec="seconds")),
        )
    return token


def get_user_by_session_token(token: str) -> dict | None:
    now = datetime.utcnow()
    if using_postgres():
        with get_postgres_connection() as connection:
            row = connection.execute(
                """
                SELECT ls.expires_at, u.id, u.nickname, u.email
                FROM login_sessions ls
                JOIN users u ON u.id = ls.user_id
                WHERE ls.token = %s
                """,
                (token,),
            ).fetchone()
            if row is None:
                return None
            expires_at = row["expires_at"]
            if expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)
            if expires_at <= now:
                connection.execute("DELETE FROM login_sessions WHERE token = %s", (token,))
                return None
        return {"id": row["id"], "nickname": row["nickname"], "email": row["email"]}

    with get_sqlite_connection() as connection:
        row = connection.execute(
            """
            SELECT ls.expires_at, u.id, u.nickname, u.email
            FROM login_sessions ls
            JOIN users u ON u.id = ls.user_id
            WHERE ls.token = ?
            """,
            (token,),
        ).fetchone()
        if row is None:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at <= now:
            connection.execute("DELETE FROM login_sessions WHERE token = ?", (token,))
            return None
    return {"id": row["id"], "nickname": row["nickname"], "email": row["email"]}


def delete_login_session(token: str) -> None:
    if using_postgres():
        with get_postgres_connection() as connection:
            connection.execute("DELETE FROM login_sessions WHERE token = %s", (token,))
        return

    with get_sqlite_connection() as connection:
        connection.execute("DELETE FROM login_sessions WHERE token = ?", (token,))


def create_password_reset_code(email: str, code: str, expiry_minutes: int = 10) -> int | None:
    user = get_user_by_email(email)
    if user is None:
        return None

    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)

    if using_postgres():
        with get_postgres_connection() as connection:
            connection.execute(
                "DELETE FROM password_reset_codes WHERE user_id = %s OR expires_at <= %s",
                (user["id"], datetime.utcnow()),
            )
            connection.execute(
                """
                INSERT INTO password_reset_codes (user_id, email, code_hash, expires_at)
                VALUES (%s, %s, %s, %s)
                """,
                (user["id"], user["email"], code_hash, expires_at),
            )
        return int(user["id"])

    with get_sqlite_connection() as connection:
        connection.execute(
            "DELETE FROM password_reset_codes WHERE user_id = ? OR expires_at <= ?",
            (user["id"], datetime.utcnow().isoformat(timespec="seconds")),
        )
        connection.execute(
            """
            INSERT INTO password_reset_codes (user_id, email, code_hash, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (user["id"], user["email"], code_hash, expires_at.isoformat(timespec="seconds")),
        )
    return int(user["id"])


def reset_password_with_code(email: str, code: str, new_password: str) -> tuple[bool, str]:
    user = get_user_by_email(email)
    if user is None:
        return False, "这个邮箱还没有注册。"

    try:
        password_hash = _hash_password(new_password)
    except ValueError as exc:
        return False, str(exc)

    code_hash = hashlib.sha256(code.strip().encode("utf-8")).hexdigest()

    if using_postgres():
        with get_postgres_connection() as connection:
            row = connection.execute(
                """
                SELECT id, expires_at, used_at
                FROM password_reset_codes
                WHERE user_id = %s AND email = %s AND code_hash = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (user["id"], user["email"], code_hash),
            ).fetchone()
            if row is None:
                return False, "验证码不正确。"
            expires_at = row["expires_at"]
            if expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)
            if row["used_at"]:
                return False, "这个验证码已经用过了。"
            if expires_at <= datetime.utcnow():
                return False, "验证码已过期，请重新获取。"

            connection.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user["id"]))
            connection.execute("UPDATE password_reset_codes SET used_at = CURRENT_TIMESTAMP WHERE id = %s", (row["id"],))
            connection.execute("DELETE FROM login_sessions WHERE user_id = %s", (user["id"],))
        return True, "密码已重置，请用新密码登录。"

    with get_sqlite_connection() as connection:
        row = connection.execute(
            """
            SELECT id, expires_at, used_at
            FROM password_reset_codes
            WHERE user_id = ? AND email = ? AND code_hash = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user["id"], user["email"], code_hash),
        ).fetchone()
        if row is None:
            return False, "验证码不正确。"
        if row["used_at"]:
            return False, "这个验证码已经用过了。"
        if datetime.fromisoformat(row["expires_at"]) <= datetime.utcnow():
            return False, "验证码已过期，请重新获取。"
        connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user["id"]))
        connection.execute("UPDATE password_reset_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
        connection.execute("DELETE FROM login_sessions WHERE user_id = ?", (user["id"],))
    return True, "密码已重置，请用新密码登录。"


def get_user_preferences(user_id: int) -> dict:
    if using_postgres():
        with get_postgres_connection() as connection:
            row = connection.execute(
                """
                SELECT favorite_flavors, disliked_ingredients, diet_goal,
                       budget_level, cooking_time_limit, vegetarian_preference
                FROM user_preferences
                WHERE user_id = %s
                """,
                (user_id,),
            ).fetchone()
        return dict(row) if row else {}

    with get_sqlite_connection() as connection:
        row = connection.execute(
            """
            SELECT favorite_flavors, disliked_ingredients, diet_goal,
                   budget_level, cooking_time_limit, vegetarian_preference
            FROM user_preferences
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else {}


def save_user_preferences(user_id: int, payload: dict) -> None:
    if using_postgres():
        with get_postgres_connection() as connection:
            connection.execute(
                """
                INSERT INTO user_preferences (
                    user_id, favorite_flavors, disliked_ingredients, diet_goal,
                    budget_level, cooking_time_limit, vegetarian_preference, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    favorite_flavors = EXCLUDED.favorite_flavors,
                    disliked_ingredients = EXCLUDED.disliked_ingredients,
                    diet_goal = EXCLUDED.diet_goal,
                    budget_level = EXCLUDED.budget_level,
                    cooking_time_limit = EXCLUDED.cooking_time_limit,
                    vegetarian_preference = EXCLUDED.vegetarian_preference,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    payload.get("favorite_flavors", ""),
                    payload.get("disliked_ingredients", ""),
                    payload.get("diet_goal", "均衡饮食"),
                    payload.get("budget_level", "中等预算"),
                    payload.get("cooking_time_limit", "30 分钟内"),
                    payload.get("vegetarian_preference", "不限"),
                ),
            )
        return

    with get_sqlite_connection() as connection:
        connection.execute(
            """
            INSERT INTO user_preferences (
                user_id, favorite_flavors, disliked_ingredients, diet_goal,
                budget_level, cooking_time_limit, vegetarian_preference, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                favorite_flavors = excluded.favorite_flavors,
                disliked_ingredients = excluded.disliked_ingredients,
                diet_goal = excluded.diet_goal,
                budget_level = excluded.budget_level,
                cooking_time_limit = excluded.cooking_time_limit,
                vegetarian_preference = excluded.vegetarian_preference,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                payload.get("favorite_flavors", ""),
                payload.get("disliked_ingredients", ""),
                payload.get("diet_goal", "均衡饮食"),
                payload.get("budget_level", "中等预算"),
                payload.get("cooking_time_limit", "30 分钟内"),
                payload.get("vegetarian_preference", "不限"),
            ),
        )


def record_action(user_id: int, recipe_id: int, action_type: str) -> None:
    if using_postgres():
        with get_postgres_connection() as connection:
            connection.execute(
                "INSERT INTO user_actions (user_id, recipe_id, action_type) VALUES (%s, %s, %s)",
                (user_id, recipe_id, action_type),
            )
        return

    with get_sqlite_connection() as connection:
        connection.execute(
            "INSERT INTO user_actions (user_id, recipe_id, action_type) VALUES (?, ?, ?)",
            (user_id, recipe_id, action_type),
        )


def record_query_signal(
    user_id: int,
    flavor_tags: list[str] | None = None,
    cuisine_groups: list[str] | None = None,
    scene: str = "",
) -> None:
    payload = (
        user_id,
        "|".join(flavor_tags or []),
        "|".join(cuisine_groups or []),
        scene,
    )
    if using_postgres():
        with get_postgres_connection() as connection:
            connection.execute(
                """
                INSERT INTO user_query_signals (user_id, flavor_tags, cuisine_groups, scene)
                VALUES (%s, %s, %s, %s)
                """,
                payload,
            )
        return

    with get_sqlite_connection() as connection:
        connection.execute(
            """
            INSERT INTO user_query_signals (user_id, flavor_tags, cuisine_groups, scene)
            VALUES (?, ?, ?, ?)
            """,
            payload,
        )


def get_favorite_recipes(user_id: int) -> list[int]:
    query = """
        SELECT recipe_id
        FROM user_actions
        WHERE user_id = {placeholder} AND action_type = 'favorite'
        ORDER BY created_at DESC
    """
    if using_postgres():
        with get_postgres_connection() as connection:
            rows = connection.execute(query.format(placeholder="%s"), (user_id,)).fetchall()
    else:
        with get_sqlite_connection() as connection:
            rows = connection.execute(query.format(placeholder="?"), (user_id,)).fetchall()

    seen = set()
    result = []
    for row in rows:
        recipe_id = row["recipe_id"]
        if recipe_id not in seen:
            result.append(recipe_id)
            seen.add(recipe_id)
    return result


def get_user_action_counts(user_id: int, action_type: str) -> dict[int, int]:
    sql = """
        SELECT recipe_id, COUNT(*) AS count
        FROM user_actions
        WHERE user_id = {p1} AND action_type = {p2}
        GROUP BY recipe_id
    """
    params = (user_id, action_type)
    if using_postgres():
        with get_postgres_connection() as connection:
            rows = connection.execute(sql.format(p1="%s", p2="%s"), params).fetchall()
    else:
        with get_sqlite_connection() as connection:
            rows = connection.execute(sql.format(p1="?", p2="?"), params).fetchall()
    return {row["recipe_id"]: row["count"] for row in rows}


def get_action_totals(user_id: int) -> dict[str, int]:
    sql = """
        SELECT action_type, COUNT(*) AS count
        FROM user_actions
        WHERE user_id = {p}
        GROUP BY action_type
    """
    if using_postgres():
        with get_postgres_connection() as connection:
            rows = connection.execute(sql.format(p="%s"), (user_id,)).fetchall()
    else:
        with get_sqlite_connection() as connection:
            rows = connection.execute(sql.format(p="?"), (user_id,)).fetchall()
    return {row["action_type"]: row["count"] for row in rows}


def get_recent_recipe_actions(user_id: int, action_type: str, limit: int = 5) -> list[dict]:
    sql = """
        SELECT recipe_id, action_type, MAX(created_at) AS created_at, MAX(id) AS latest_id
        FROM user_actions
        WHERE user_id = {p1} AND action_type = {p2}
        GROUP BY recipe_id, action_type
        ORDER BY latest_id DESC
        LIMIT {p3}
    """
    params = (user_id, action_type, limit)
    if using_postgres():
        with get_postgres_connection() as connection:
            rows = connection.execute(sql.format(p1="%s", p2="%s", p3="%s"), params).fetchall()
    else:
        with get_sqlite_connection() as connection:
            rows = connection.execute(sql.format(p1="?", p2="?", p3="?"), params).fetchall()
    return [dict(row) for row in rows]


def get_recent_user_actions(user_id: int, limit: int = 120) -> list[dict]:
    sql = """
        SELECT id, recipe_id, action_type, created_at
        FROM user_actions
        WHERE user_id = {p1}
        ORDER BY id DESC
        LIMIT {p2}
    """
    params = (user_id, limit)
    if using_postgres():
        with get_postgres_connection() as connection:
            rows = connection.execute(sql.format(p1="%s", p2="%s"), params).fetchall()
    else:
        with get_sqlite_connection() as connection:
            rows = connection.execute(sql.format(p1="?", p2="?"), params).fetchall()
    return [dict(row) for row in rows]


def get_recent_query_signals(user_id: int, limit: int = 40) -> list[dict]:
    sql = """
        SELECT id, flavor_tags, cuisine_groups, scene, created_at
        FROM user_query_signals
        WHERE user_id = {p1}
        ORDER BY id DESC
        LIMIT {p2}
    """
    params = (user_id, limit)
    if using_postgres():
        with get_postgres_connection() as connection:
            rows = connection.execute(sql.format(p1="%s", p2="%s"), params).fetchall()
    else:
        with get_sqlite_connection() as connection:
            rows = connection.execute(sql.format(p1="?", p2="?"), params).fetchall()
    return [dict(row) for row in rows]


def record_profile_feedback(user_id: int, profile_type: str, profile_value: str, feedback_type: str) -> None:
    params = (user_id, profile_type, profile_value, feedback_type)
    if using_postgres():
        with get_postgres_connection() as connection:
            connection.execute(
                """
                INSERT INTO profile_feedback (user_id, profile_type, profile_value, feedback_type)
                VALUES (%s, %s, %s, %s)
                """,
                params,
            )
        return

    with get_sqlite_connection() as connection:
        connection.execute(
            """
            INSERT INTO profile_feedback (user_id, profile_type, profile_value, feedback_type)
            VALUES (?, ?, ?, ?)
            """,
            params,
        )


def get_profile_feedback_summary(user_id: int) -> dict[tuple[str, str], dict[str, int]]:
    sql = """
        SELECT profile_type, profile_value, feedback_type, COUNT(*) AS count
        FROM profile_feedback
        WHERE user_id = {p}
        GROUP BY profile_type, profile_value, feedback_type
    """
    if using_postgres():
        with get_postgres_connection() as connection:
            rows = connection.execute(sql.format(p="%s"), (user_id,)).fetchall()
    else:
        with get_sqlite_connection() as connection:
            rows = connection.execute(sql.format(p="?"), (user_id,)).fetchall()

    summary: dict[tuple[str, str], dict[str, int]] = {}
    for row in rows:
        key = (row["profile_type"], row["profile_value"])
        summary.setdefault(key, {"confirm": 0, "downvote": 0})
        summary[key][row["feedback_type"]] = row["count"]
    return summary


def get_preference_summary(preferences: dict) -> list[str]:
    summary = []
    flavors = preferences.get("favorite_flavors", "")
    if flavors:
        summary.append(f"偏爱口味：{flavors.replace('|', '、')}")
    if preferences.get("diet_goal"):
        summary.append(f"长期目标：{preferences['diet_goal']}")
    if preferences.get("budget_level"):
        summary.append(f"预算：{preferences['budget_level']}")
    if preferences.get("cooking_time_limit"):
        summary.append(f"做饭时间：{preferences['cooking_time_limit']}")
    if preferences.get("disliked_ingredients"):
        summary.append(f"忌口：{preferences['disliked_ingredients']}")
    if preferences.get("vegetarian_preference"):
        summary.append(f"饮食倾向：{preferences['vegetarian_preference']}")
    return summary


def _normalize_recipe_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {}
    for column in RECIPE_COLUMNS:
        value = row.get(column)
        if value != value:  # NaN
            value = None
        if column in {"id", "cook_time_minutes", "is_spicy", "is_vegetarian"} and value is not None:
            value = int(value)
        normalized[column] = value
    return normalized


def get_recipes_from_sqlite() -> list[dict[str, Any]]:
    import csv

    with RECIPES_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [_normalize_recipe_row(row) for row in reader]


def postgres_recipes_available() -> bool:
    if not using_postgres():
        return False
    try:
        with get_postgres_connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM recipes").fetchone()
        return bool(row and row["count"] > 0)
    except Exception:
        return False


def get_all_recipes() -> list[dict[str, Any]]:
    if postgres_recipes_available():
        with get_postgres_connection() as connection:
            rows = connection.execute(
                f"SELECT {', '.join(RECIPE_COLUMNS)} FROM recipes ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]
    return get_recipes_from_sqlite()


def get_recipe_record_by_id(recipe_id: int) -> dict[str, Any] | None:
    if postgres_recipes_available():
        with get_postgres_connection() as connection:
            row = connection.execute(
                f"SELECT {', '.join(RECIPE_COLUMNS)} FROM recipes WHERE id = %s",
                (recipe_id,),
            ).fetchone()
        return dict(row) if row else None

    for recipe in get_recipes_from_sqlite():
        if recipe["id"] == recipe_id:
            return recipe
    return None


def import_recipes_csv_to_postgres() -> int:
    if not postgres_configured():
        raise RuntimeError("PostgreSQL 当前未启用，无法导入菜单。")

    rows = get_recipes_from_sqlite()
    with get_postgres_connection() as connection:
        for row in rows:
            connection.execute(
                """
                INSERT INTO recipes (
                    id, name, cuisine, staple_category, cuisine_group, beverage_category,
                    flavor_tags, scene_tags, diet_tags, feature_tags, budget_level,
                    cook_time_minutes, difficulty, ingredients, is_spicy, is_vegetarian,
                    calorie_level, description
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    cuisine = EXCLUDED.cuisine,
                    staple_category = EXCLUDED.staple_category,
                    cuisine_group = EXCLUDED.cuisine_group,
                    beverage_category = EXCLUDED.beverage_category,
                    flavor_tags = EXCLUDED.flavor_tags,
                    scene_tags = EXCLUDED.scene_tags,
                    diet_tags = EXCLUDED.diet_tags,
                    feature_tags = EXCLUDED.feature_tags,
                    budget_level = EXCLUDED.budget_level,
                    cook_time_minutes = EXCLUDED.cook_time_minutes,
                    difficulty = EXCLUDED.difficulty,
                    ingredients = EXCLUDED.ingredients,
                    is_spicy = EXCLUDED.is_spicy,
                    is_vegetarian = EXCLUDED.is_vegetarian,
                    calorie_level = EXCLUDED.calorie_level,
                    description = EXCLUDED.description
                """,
                tuple(row[column] for column in RECIPE_COLUMNS),
            )
    return len(rows)


def migrate_sqlite_user_data_to_postgres() -> dict[str, int]:
    if not postgres_configured():
        raise RuntimeError("PostgreSQL 当前未启用，无法迁移数据。")

    migrated_counts = {
        "users": 0,
        "user_preferences": 0,
        "user_actions": 0,
        "login_sessions": 0,
        "password_reset_codes": 0,
        "profile_feedback": 0,
        "user_query_signals": 0,
    }
    skipped_counts = {
        "user_preferences": 0,
        "user_actions": 0,
        "login_sessions": 0,
        "password_reset_codes": 0,
        "profile_feedback": 0,
        "user_query_signals": 0,
    }

    with get_sqlite_connection() as sqlite_conn, get_postgres_connection() as pg_conn:
        users = _sqlite_dicts(sqlite_conn.execute("SELECT * FROM users ORDER BY id"))
        valid_user_ids = {row["id"] for row in users}
        for row in users:
            pg_conn.execute(
                """
                INSERT INTO users (id, nickname, email, password_hash, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    nickname = EXCLUDED.nickname,
                    email = EXCLUDED.email,
                    password_hash = EXCLUDED.password_hash,
                    created_at = EXCLUDED.created_at
                """,
                (row["id"], row["nickname"], row["email"], row["password_hash"], row["created_at"]),
            )
        migrated_counts["users"] = len(users)

        preferences = _sqlite_dicts(sqlite_conn.execute("SELECT * FROM user_preferences"))
        for row in preferences:
            if row["user_id"] not in valid_user_ids:
                skipped_counts["user_preferences"] += 1
                continue
            pg_conn.execute(
                """
                INSERT INTO user_preferences (
                    user_id, favorite_flavors, disliked_ingredients, diet_goal,
                    budget_level, cooking_time_limit, vegetarian_preference, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    favorite_flavors = EXCLUDED.favorite_flavors,
                    disliked_ingredients = EXCLUDED.disliked_ingredients,
                    diet_goal = EXCLUDED.diet_goal,
                    budget_level = EXCLUDED.budget_level,
                    cooking_time_limit = EXCLUDED.cooking_time_limit,
                    vegetarian_preference = EXCLUDED.vegetarian_preference,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    row["user_id"],
                    row["favorite_flavors"],
                    row["disliked_ingredients"],
                    row["diet_goal"],
                    row["budget_level"],
                    row["cooking_time_limit"],
                    row["vegetarian_preference"],
                    row["updated_at"],
                ),
            )
            migrated_counts["user_preferences"] += 1

        table_statements = {
            "user_actions": "INSERT INTO user_actions (id, user_id, recipe_id, action_type, created_at) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            "login_sessions": "INSERT INTO login_sessions (token, user_id, expires_at, created_at) VALUES (%s, %s, %s, %s) ON CONFLICT (token) DO UPDATE SET user_id = EXCLUDED.user_id, expires_at = EXCLUDED.expires_at, created_at = EXCLUDED.created_at",
            "password_reset_codes": "INSERT INTO password_reset_codes (id, user_id, email, code_hash, expires_at, used_at, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            "profile_feedback": "INSERT INTO profile_feedback (id, user_id, profile_type, profile_value, feedback_type, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            "user_query_signals": "INSERT INTO user_query_signals (id, user_id, flavor_tags, cuisine_groups, scene, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        }
        for table_name, statement in table_statements.items():
            rows = _sqlite_dicts(sqlite_conn.execute(f"SELECT * FROM {table_name}"))
            for row in rows:
                if row["user_id"] not in valid_user_ids:
                    skipped_counts[table_name] += 1
                    continue
                pg_conn.execute(statement, tuple(row.values()))
                migrated_counts[table_name] += 1

        pg_conn.execute("SELECT setval(pg_get_serial_sequence('users', 'id'), GREATEST((SELECT COALESCE(MAX(id), 1) FROM users), 1), true)")
        for table_name in ["user_actions", "password_reset_codes", "profile_feedback", "user_query_signals"]:
            pg_conn.execute(
                f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), GREATEST((SELECT COALESCE(MAX(id), 1) FROM {table_name}), 1), true)"
            )

    return {
        **migrated_counts,
        **{f"skipped_{table_name}": count for table_name, count in skipped_counts.items()},
    }
