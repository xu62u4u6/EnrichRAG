"""SQLite-backed auth and per-user history storage."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from enrichrag.settings import settings

SESSION_TTL_DAYS = 7
PBKDF2_ITERATIONS = 240_000
SALT_BYTES = 16
KEY_BYTES = 32


def utcnow() -> datetime:
    return datetime.now(UTC)


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.auth_db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS, KEY_BYTES)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(derived).decode("ascii"),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
    except ValueError:
        return False
    salt = base64.b64decode(salt_b64.encode("ascii"))
    expected = base64.b64decode(digest_b64.encode("ascii"))
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(iterations),
        len(expected),
    )
    return hmac.compare_digest(actual, expected)


def init_storage() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                disease_context TEXT NOT NULL,
                gene_count INTEGER NOT NULL,
                input_genes_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        _ensure_default_user(conn)
        conn.commit()


def _ensure_default_user(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE email = ?",
        (settings.auth_default_email,),
    ).fetchone()
    desired_display = "Lab Operator"
    if row is None:
        conn.execute(
            """
            INSERT INTO users (email, password_hash, display_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                settings.auth_default_email,
                hash_password(settings.auth_default_password),
                desired_display,
                utcnow().isoformat(),
            ),
        )


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, display_name FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "display_name": row["display_name"],
        }


def create_user(email: str, password: str, display_name: str) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    normalized_display = display_name.strip() or normalized_email
    with _connect() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
        if existing is not None:
            raise ValueError("Email already exists.")
        cur = conn.execute(
            """
            INSERT INTO users (email, password_hash, display_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                normalized_email,
                hash_password(password),
                normalized_display,
                utcnow().isoformat(),
            ),
        )
        conn.commit()
        return {
            "id": int(cur.lastrowid),
            "email": normalized_email,
            "display_name": normalized_display,
        }


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = utcnow()
    expires_at = now + timedelta(days=SESSION_TTL_DAYS)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, now.isoformat(), expires_at.isoformat()),
        )
        conn.commit()
    return token


def get_user_by_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT users.id, users.email, users.display_name, sessions.expires_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
        if row is None:
            return None
        if datetime.fromisoformat(row["expires_at"]) <= utcnow():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "display_name": row["display_name"],
        }


def delete_session(token: str | None) -> None:
    if not token:
        return
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


def save_analysis_run(user_id: int, result: dict[str, Any]) -> int:
    genes = result.get("input_genes") or result.get("genes") or []
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO analysis_runs (
                user_id,
                disease_context,
                gene_count,
                input_genes_json,
                result_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                result.get("disease_context") or "Analysis",
                len(genes),
                json.dumps(genes, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
                utcnow().isoformat(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_analysis_runs(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, disease_context, gene_count, input_genes_json, created_at
            FROM analysis_runs
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "disease_context": row["disease_context"],
            "gene_count": row["gene_count"],
            "input_genes": json.loads(row["input_genes_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_analysis_run(user_id: int, analysis_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, result_json, created_at
            FROM analysis_runs
            WHERE id = ? AND user_id = ?
            """,
            (analysis_id, user_id),
        ).fetchone()
    if row is None:
        return None
    data = json.loads(row["result_json"])
    data["history_id"] = row["id"]
    data["saved_at"] = row["created_at"]
    return data


def delete_analysis_run(user_id: int, analysis_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM analysis_runs WHERE id = ? AND user_id = ?",
            (analysis_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


def clear_analysis_runs(user_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM analysis_runs WHERE user_id = ?", (user_id,))
        conn.commit()
