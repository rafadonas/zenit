from __future__ import annotations

import argparse
import getpass
import sys

import psycopg
from psycopg.errors import UniqueViolation
from pwdlib import PasswordHash

from zenit_api.config import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zenit-user",
        description="Create a local MVP reviewer without exposing its password.",
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--road-code", required=True)
    parser.add_argument("--role", required=True, choices=("manager", "supervisor"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    email = args.email.strip().lower()
    display_name = args.display_name.strip()
    if "@" not in email or not display_name:
        raise SystemExit("A valid email and non-blank display name are required")

    password = getpass.getpass("Password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    if len(password) > 1024:
        raise SystemExit("Password must contain at most 1024 characters")

    settings = get_settings()
    database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    password_hash = PasswordHash.recommended().hash(password)
    del password, confirmation

    try:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id FROM road WHERE code = %s", (args.road_code,))
            road = cursor.fetchone()
            if road is None:
                raise SystemExit(f"Road code {args.road_code!r} does not exist")
            cursor.execute(
                """
                INSERT INTO app_user (email, password_hash, display_name)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (email, password_hash, display_name),
            )
            user_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO road_user_role (user_id, road_id, role, data_status)
                VALUES (%s, %s, %s, 'prepared')
                """,
                (user_id, road[0], args.role),
            )
    except UniqueViolation:
        raise SystemExit("The user or role assignment already exists") from None
    except psycopg.Error as error:
        print("Could not create the local MVP user", file=sys.stderr)
        raise SystemExit(1) from error

    print(f"Created local MVP user {user_id} with the prepared {args.role} role")
