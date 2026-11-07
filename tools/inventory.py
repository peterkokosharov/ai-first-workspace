#!/usr/bin/env python3
"""Portable workspace inventory over SQLite.

The database file ``data/inventory.db`` lives next to the project root; it is
local to this machine, never committed, and gitignored.  The schema and the seed
data are ``data/schema.sql`` and ``data/seed.sql`` and are committed.

Standard library only, no venv, no pip.

Tables: machines, services, providers, keys, models, tools, settings.
A key belongs either to a service or to a provider, never both.

Usage:
    python3 tools/inventory.py init         # create schema, load seed (re-runnable)
    python3 tools/inventory.py tables       # list tables
    python3 tools/inventory.py list TABLE   # list rows of a table
    python3 tools/inventory.py show TABLE ID # show one row
    python3 tools/inventory.py search TABLE COLUMN LIKE_STRING
    python3 tools/inventory.py sql "SELECT ..."          # read-only SELECT only
    python3 tools/inventory.py setting KEY [VALUE]       # read or write a setting

Exit codes: 0 ok, 1 not found, 2 database error, 3 usage error.
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_DB = 2
EXIT_USAGE = 3

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB = DATA / "inventory.db"
SCHEMA = DATA / "schema.sql"
SEED = DATA / "seed.sql"

READ_ONLY_PREFIX = re.compile(r"\s*(SELECT|WITH)\b", re.IGNORECASE)


class InventoryError(Exception):
    exit_code = EXIT_DB

    def __init__(self, message: str, exit_code: int | None = None):
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class NotFoundError(InventoryError):
    exit_code = EXIT_NOT_FOUND


class UsageError(InventoryError):
    exit_code = EXIT_USAGE


# -------------------------------------------------------------------------------------- helpers


def _connect() -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(str(DB))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as exc:
        raise InventoryError(f"cannot open database {DB}: {exc}") from exc


def _read_sql_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InventoryError(f"cannot read {path}: {exc.strerror}") from exc


def _tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [row["name"] for row in rows]


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})")
    return [row["name"] for row in rows]


def _fmt_row(row: sqlite3.Row) -> str:
    out = []
    for key in row.keys():
        value = row[key]
        out.append(f"{key} = {value!r}" if value is not None else f"{key} = NULL")
    return "\n  ".join(out)


def _is_read_only(statement: str) -> bool:
    return bool(READ_ONLY_PREFIX.match(statement))


# -------------------------------------------------------------------------------------- commands


def cmd_init(_args) -> int:
    if not SCHEMA.exists():
        raise InventoryError(f"schema file not found: {SCHEMA}", EXIT_DB)
    conn = _connect()
    try:
        conn.executescript(_read_sql_file(SCHEMA))
        conn.commit()
        if SEED.exists():
            conn.executescript(_read_sql_file(SEED))
            conn.commit()
    finally:
        conn.close()
    print(f"initialized {DB} (schema: {SCHEMA}; seed: {SEED})")
    return EXIT_OK


def cmd_tables(_args) -> int:
    conn = _connect()
    try:
        names = _tables(conn)
    finally:
        conn.close()
    if not names:
        print("(no tables)")
        return EXIT_OK
    for name in names:
        print(name)
    return EXIT_OK


def cmd_list(args) -> int:
    table = args.table
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise UsageError(f"invalid table name: {table!r}")
    conn = _connect()
    try:
        tables = _tables(conn)
        if table not in tables:
            raise NotFoundError(f"no such table: {table}")
        columns = _columns(conn, table)
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
    finally:
        conn.close()
    if not rows:
        print(f"table {table} is empty")
        return EXIT_OK
    print(f"table {table} ({len(rows)} row{'s' if len(rows) != 1 else ''}):")
    for row in rows:
        print(f"  [{row[columns[0]]}] {_fmt_row(row)}")
    return EXIT_OK


def cmd_show(args) -> int:
    table = args.table
    row_id = args.id
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise UsageError(f"invalid table name: {table!r}")
    conn = _connect()
    try:
        tables = _tables(conn)
        if table not in tables:
            raise NotFoundError(f"no such table: {table}")
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise NotFoundError(f"{table} id={row_id} not found")
    print(f"{table} id={row_id}:")
    print("  " + _fmt_row(row))
    return EXIT_OK


def cmd_search(args) -> int:
    table = args.table
    column = args.column
    pattern = args.pattern
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise UsageError(f"invalid table name: {table!r}")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", column):
        raise UsageError(f"invalid column name: {column!r}")
    conn = _connect()
    try:
        tables = _tables(conn)
        if table not in tables:
            raise NotFoundError(f"no such table: {table}")
        columns = _columns(conn, table)
        if column not in columns:
            raise NotFoundError(f"no such column {column} in table {table}")
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE {column} LIKE ? ORDER BY 1",
            (f"%{pattern}%",),
        ).fetchall()
    finally:
        conn.close()
    print(f"{table} where {column} like %{pattern}% ({len(rows)}):")
    for row in rows:
        print(f"  [{row['id']}] {_fmt_row(row)}")
    return EXIT_OK


def cmd_sql(args) -> int:
    statement = args.statement.strip()
    if not _is_read_only(statement):
        raise UsageError("only read-only SELECT/WITH statements are allowed")
    conn = _connect()
    try:
        cur = conn.execute(statement)
        rows = cur.fetchall()
    except sqlite3.Error as exc:
        raise InventoryError(f"SQL error: {exc}") from exc
    finally:
        conn.close()
    if not rows:
        print("(no rows)")
        return EXIT_OK
    columns = [desc[0] for desc in cur.description]
    widths = [len(c) for c in columns]
    for row in rows:
        for index, value in enumerate(row):
            text = "" if value is None else str(value)
            widths[index] = max(widths[index], len(text))
    header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
    sep = "-+-".join("-" * widths[i] for i in range(len(columns)))
    print(header)
    print(sep)
    for row in rows:
        print(" | ".join(("" if value is None else str(value)).ljust(widths[i])
                         for i, value in enumerate(row)))
    return EXIT_OK


def cmd_setting(args) -> int:
    key = args.key
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None and args.value is None:
            raise NotFoundError(f"setting {key!r} not found")
        if args.value is not None:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = datetime('now')",
                (key, args.value),
            )
            conn.commit()
            print(f"setting {key!r} = {args.value!r}")
            return EXIT_OK
        value = row["value"]
        print(f"{key} = {value!r}" if value is not None else f"{key} = NULL")
        return EXIT_OK
    finally:
        conn.close()


# -------------------------------------------------------------------------------------- command line


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="inventory.py",
        description="Portable workspace inventory over SQLite.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create schema and load seed data")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("tables", help="list tables")
    p.set_defaults(func=cmd_tables)

    p = sub.add_parser("list", help="list rows of a table")
    p.add_argument("table")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="show one row by id")
    p.add_argument("table")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("search", help="search rows by column LIKE pattern")
    p.add_argument("table")
    p.add_argument("column")
    p.add_argument("pattern")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("sql", help="read-only SELECT / WITH query")
    p.add_argument("statement")
    p.set_defaults(func=cmd_sql)

    p = sub.add_parser("setting", help="read or write a setting")
    p.add_argument("key")
    p.add_argument("value", nargs="?")
    p.set_defaults(func=cmd_setting)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except InventoryError as exc:
        print(f"inventory.py: {exc}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        print("inventory.py: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
