import hashlib
import os
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "data" / "tastepilot.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
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

    password_hash = _hash_password(password)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO users (nickname, email, password_hash) VALUES (?, ?, ?)",
                (nickname, email.lower(), password_hash),
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
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, nickname, email, password_hash FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()

    if row is None:
        return None
    if not _verify_password(password, row["password_hash"]):
        return None

    return {"id": row["id"], "nickname": row["nickname"], "email": row["email"]}


def get_user_preferences(user_id: int) -> dict:
    with get_connection() as connection:
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
    with get_connection() as connection:
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
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO user_actions (user_id, recipe_id, action_type) VALUES (?, ?, ?)",
            (user_id, recipe_id, action_type),
        )


def get_favorite_recipes(user_id: int) -> list[int]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT recipe_id
            FROM user_actions
            WHERE user_id = ? AND action_type = 'favorite'
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()

    seen = set()
    result = []
    for row in rows:
        recipe_id = row["recipe_id"]
        if recipe_id not in seen:
            result.append(recipe_id)
            seen.add(recipe_id)
    return result


def get_user_action_counts(user_id: int, action_type: str) -> dict[int, int]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT recipe_id, COUNT(*) AS count
            FROM user_actions
            WHERE user_id = ? AND action_type = ?
            GROUP BY recipe_id
            """,
            (user_id, action_type),
        ).fetchall()

    return {row["recipe_id"]: row["count"] for row in rows}


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
