"""Episode 6: the record (Acme Cloud's help center in Postgres) and the application that changes it.

The application saves an article in one transaction and sets `updated_at`; deletes are hard deletes. The one
migration is a raw SQL statement, run the way a migration runs, outside the application. Logical decoding
(`wal_level=logical`, a `test_decoding` slot) is on for the CDC designs.

The text a design indexes for an article is its title and body; its `source` is its public URL, as a loader
for a website would set it.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime

import psycopg
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

DSN = "postgresql://acme:acme@127.0.0.1:5446/helpcenter"
URL = "https://help.acme.cloud/"
SLOT = "bd6_cdc"

SPLITTER = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, add_start_index=True)  # the tutorial's

SCHEMA = """
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS articles CASCADE;
CREATE TABLE articles (
    id          integer PRIMARY KEY,
    slug        text NOT NULL UNIQUE,
    title       text NOT NULL,
    category    text NOT NULL,
    body        text NOT NULL,
    created_at  timestamptz NOT NULL,
    updated_at  timestamptz NOT NULL
);
CREATE INDEX articles_updated_at ON articles (updated_at);
-- the same-database design keeps its chunks here, written in the save's transaction
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE chunks (
    id          bigserial PRIMARY KEY,
    article_id  integer NOT NULL REFERENCES articles (id) ON DELETE CASCADE,
    n           integer NOT NULL,
    source      text NOT NULL,
    text        text NOT NULL,
    embedding   vector(384) NOT NULL
);
CREATE INDEX chunks_article ON chunks (article_id);
"""


def text(row: dict) -> str:
    return row["title"] + "\n\n" + row["body"]


def article_hash(row: dict) -> str:
    """What the query-time check compares: md5 of title || E'\\n\\n' || body, the same in SQL and here."""
    return hashlib.md5(text(row).encode()).hexdigest()


def source(row: dict) -> str:
    return URL + row["slug"]


def document(row: dict) -> Document:
    return Document(page_content=text(row), metadata={"source": source(row), "article_id": int(row["id"])})


def chunks(row: dict) -> list[Document]:
    """The tutorial's split of one article; every chunk carries source, article_id and start_index."""
    return SPLITTER.split_documents([document(row)])


_chunk_cache: dict[str, list[str]] = {}


def chunk_texts(row: dict) -> list[str]:
    h = article_hash(row)
    if h not in _chunk_cache:
        _chunk_cache[h] = [d.page_content for d in chunks(row)]
    return _chunk_cache[h]


class Record:
    def __init__(self, dsn: str = DSN):
        self.c = psycopg.connect(dsn, autocommit=True)

    # ---- setup
    def reset(self, articles: list[dict], slot: bool = False) -> None:
        self.drop_slot()
        self.c.execute(SCHEMA)
        with self.c.cursor().copy("COPY articles (id, slug, title, category, body, created_at, updated_at) FROM STDIN") as cp:
            for a in articles:
                cp.write_row((a["id"], a["slug"], a["title"], a["category"], a["body"], a["created_at"], a["updated_at"]))
        self.c.execute("ANALYZE articles")
        if slot:
            self.c.execute(f"SELECT pg_create_logical_replication_slot('{SLOT}', 'test_decoding')")

    def drop_slot(self) -> None:
        if self.c.execute("SELECT 1 FROM pg_replication_slots WHERE slot_name = %s", (SLOT,)).fetchone():
            self.c.execute("SELECT pg_drop_replication_slot(%s)", (SLOT,))

    # ---- the application
    def save(self, row: dict, at: str, hook=None) -> None:
        """One article saved by the application: one transaction; `hook(cursor, row)` runs inside it."""
        with self.c.transaction():
            with self.c.cursor() as cur:
                cur.execute("""INSERT INTO articles (id, slug, title, category, body, created_at, updated_at)
                               VALUES (%(id)s, %(slug)s, %(title)s, %(category)s, %(body)s, %(created_at)s, %(at)s)
                               ON CONFLICT (id) DO UPDATE SET slug = EXCLUDED.slug, title = EXCLUDED.title,
                               category = EXCLUDED.category, body = EXCLUDED.body, updated_at = EXCLUDED.updated_at""",
                            row | {"at": at})
                if hook is not None:
                    hook(cur, row)

    def delete(self, article_id: int) -> None:
        self.c.execute("DELETE FROM articles WHERE id = %s", (article_id,))

    def sql(self, statement: str) -> int:
        return self.c.execute(statement).rowcount

    # ---- reading it
    def rows(self, where: str = "", params=()) -> list[dict]:
        cur = self.c.cursor(row_factory=psycopg.rows.dict_row)
        return cur.execute(f"SELECT id, slug, title, category, body, created_at, updated_at FROM articles {where} "
                           f"ORDER BY id", params).fetchall()

    def row(self, article_id: int) -> dict | None:
        r = self.rows("WHERE id = %s", (article_id,))
        return r[0] if r else None

    def hashes(self, ids: list[int]) -> dict[int, str]:
        return dict(self.c.execute("SELECT id, md5(title || E'\\n\\n' || body) FROM articles WHERE id = ANY(%s)",
                                   (list(ids),)).fetchall())

    def changes(self) -> list[tuple[str, int]]:
        """Committed changes to `articles` since the last call, from the logical decoding slot, in commit order."""
        out = []
        for (data,) in self.c.execute("SELECT data FROM pg_logical_slot_get_changes(%s, NULL, NULL)", (SLOT,)):
            m = re.match(r"table public\.articles: (INSERT|UPDATE|DELETE): id\[integer\]:(\d+)", data)
            if m:
                out.append((m.group(1), int(m.group(2))))
        return out


def iso(t: datetime | str) -> str:
    return t if isinstance(t, str) else t.isoformat()
