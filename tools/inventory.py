#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Portable workspace inventory over SQLite.

The database file ``data/inventory.db`` lives next to the project root; it is
local to this machine, never committed, and gitignored.  The schema and the seed
data are ``data/schema.sql`` and ``data/seed.sql`` and are committed.

Standard library only, no venv, no pip.

Tables: machines, services, providers, keys, models, tools.
A key belongs either to a service or to a provider, never both.

Usage:
    python3 tools/inventory.py init         # create schema, load seed (re-runnable)
    python3 tools/inventory.py tables       # list tables
    python3 tools/inventory.py list TABLE [--table]  # list rows (--table: one line per row)
    python3 tools/inventory.py show TABLE ID # show one row
    python3 tools/inventory.py search TABLE COLUMN LIKE_STRING
    python3 tools/inventory.py sql "SELECT ..."          # read-only (database opened read-only)
    python3 tools/inventory.py key NAME     # key paths of a service or provider (never values)
    python3 tools/inventory.py add-service NAME KIND [--account A] [--notes N]
    python3 tools/inventory.py add-key PATH (--service NAME | --provider NAME) [--kind K]
                                       [--status S] [--notes N]

Key paths follow the rules of tools/secret.py: lowercase segments separated by "/",
at least two segments, no leading "/". Per-project tokens: scope/project/kind,
scope = personal | company, e.g. personal/my-project/github_token.
add-service and add-key write only to the local database (INVENTORY_DB if set);
data/seed.sql is never changed.

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
DEFAULT_DB = DATA / "inventory.db"
DB = Path(os.environ.get("INVENTORY_DB", str(DEFAULT_DB)))
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


def _connect_read_only() -> sqlite3.Connection:
    """Open the database read-only: SQLite URI ``mode=ro`` plus ``PRAGMA query_only``.

    A statement that writes (also one hidden behind ``WITH ... DELETE``) fails here,
    whatever text it starts with.
    """
    if not DB.is_file():
        raise InventoryError(f"database not found: {DB}. Run: python3 tools/inventory.py init")
    try:
        conn = sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn
    except sqlite3.Error as exc:
        raise InventoryError(f"cannot open database {DB} read-only: {exc}") from exc


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


def _print_table(columns: list[str], rows, max_width: int | None = None) -> None:
    """Print rows as aligned columns; cells longer than ``max_width`` are cut."""
    def cell(value) -> str:
        text = "" if value is None else " ".join(str(value).split())
        if max_width and len(text) > max_width:
            text = text[: max_width - 3] + "..."
        return text

    cells = [[cell(value) for value in row] for row in rows]
    widths = [len(c) for c in columns]
    for row in cells:
        for index, text in enumerate(row):
            widths[index] = max(widths[index], len(text))
    print(" | ".join(c.ljust(widths[i]) for i, c in enumerate(columns)).rstrip())
    print("-+-".join("-" * widths[i] for i in range(len(columns))))
    for row in cells:
        print(" | ".join(text.ljust(widths[i]) for i, text in enumerate(row)).rstrip())


def _connect_existing() -> sqlite3.Connection:
    """Open the database for writing, but only if it exists (never create an empty one)."""
    if not DB.is_file():
        raise InventoryError(f"database not found: {DB}. Run: python3 tools/inventory.py init")
    return _connect()


def _validate_key_path(path: str) -> str:
    """Check ``path`` with the same rules as tools/secret.py (one source of the rules)."""
    tools_dir = str(Path(__file__).resolve().parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import secret  # noqa: E402  (tools/secret.py, standard library only)

    try:
        return secret.validate_path(path)
    except secret.UsageError as exc:
        raise UsageError(str(exc)) from exc


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
    if args.table_format:
        _print_table(columns, rows, max_width=40)
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
    conn = _connect_read_only()
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
    _print_table([desc[0] for desc in cur.description], rows)
    return EXIT_OK


def cmd_key(args) -> int:
    """Key paths (never values) that belong to a service or provider NAME."""
    conn = _connect_read_only()
    try:
        rows = conn.execute(
            "SELECT k.path, k.status, k.notes, "
            "       CASE WHEN s.id IS NOT NULL THEN 'service ' || s.name "
            "            ELSE 'provider ' || p.name END AS owner "
            "FROM keys k "
            "LEFT JOIN services s ON k.service_id = s.id "
            "LEFT JOIN providers p ON k.provider_id = p.id "
            "WHERE lower(s.name) = lower(?) OR lower(p.name) = lower(?) "
            "ORDER BY k.id",
            (args.name, args.name),
        ).fetchall()
    except sqlite3.Error as exc:
        raise InventoryError(f"SQL error: {exc}") from exc
    finally:
        conn.close()
    if not rows:
        raise NotFoundError(
            f"no key for a service or provider named {args.name!r}. Add one: "
            f"python3 tools/inventory.py add-key <path> --service {args.name}")
    for row in rows:
        note = f"  ({row['notes']})" if row["notes"] else ""
        print(f"{row['path']}  [{row['status']}] {row['owner']}{note}")
    return EXIT_OK


def cmd_add_service(args) -> int:
    conn = _connect_existing()
    try:
        conn.execute(
            "INSERT INTO services (name, kind, account, notes) VALUES (?, ?, ?, ?)",
            (args.name, args.kind, args.account, args.notes),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        raise UsageError(f"cannot add service {args.name!r}: {exc}") from exc
    except sqlite3.Error as exc:
        raise InventoryError(f"SQL error: {exc}") from exc
    finally:
        conn.close()
    print(f"added service {args.name!r} ({args.kind}) to {DB}")
    return EXIT_OK


def cmd_add_key(args) -> int:
    path = _validate_key_path(args.path)
    owner_table = "services" if args.service else "providers"
    owner_name = args.service or args.provider
    kind = args.kind or path.rsplit("/", 1)[-1]
    conn = _connect_existing()
    try:
        owner = conn.execute(
            f"SELECT id FROM {owner_table} WHERE lower(name) = lower(?)", (owner_name,)
        ).fetchone()
        if owner is None:
            hint = ("python3 tools/inventory.py add-service NAME KIND" if args.service
                    else "python3 tools/inventory.py list providers")
            raise NotFoundError(f"no {owner_table[:-1]} named {owner_name!r} ({hint})")
        service_id = owner["id"] if args.service else None
        provider_id = owner["id"] if args.provider else None
        conn.execute(
            "INSERT INTO keys (path, service_id, provider_id, kind, status, notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (path, service_id, provider_id, kind, args.status, args.notes),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        raise UsageError(f"cannot add key {path!r}: {exc}") from exc
    except sqlite3.Error as exc:
        raise InventoryError(f"SQL error: {exc}") from exc
    finally:
        conn.close()
    print(f"added key path {path!r} for {owner_table[:-1]} {owner_name!r} to {DB} "
          "(only the name; store the value with tools/secret.py set)")
    return EXIT_OK


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
    p.add_argument("--table", dest="table_format", action="store_true",
                   help="compact output: one line per row, long cells cut")
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

    p = sub.add_parser("key", help="key paths of a service or provider (never values)")
    p.add_argument("name", help="service or provider name, e.g. gmail or nvidia")
    p.set_defaults(func=cmd_key)

    p = sub.add_parser("add-service", help="add a service to the local database")
    p.add_argument("name")
    p.add_argument("kind", help="e.g. mail, code hosting")
    p.add_argument("--account")
    p.add_argument("--notes")
    p.set_defaults(func=cmd_add_service)

    p = sub.add_parser("add-key", help="add a key path (not a value) to the local database")
    p.add_argument("path", help="scope/project/kind, e.g. personal/my-project/github_token")
    owner = p.add_mutually_exclusive_group(required=True)
    owner.add_argument("--service")
    owner.add_argument("--provider")
    p.add_argument("--kind", help="default: the last segment of PATH")
    p.add_argument("--status", default="active",
                   choices=["active", "planned", "broken", "retired", "unknown"])
    p.add_argument("--notes")
    p.set_defaults(func=cmd_add_key)

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
