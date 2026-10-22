"""SQLite FTS5 BM25 retrieval with CJK bigrams and exact source line spans."""
import hashlib
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path


def tokenize(text):
    text = unicodedata.normalize("NFKC", text).lower()
    result = re.findall(r"[a-z0-9_]+", text)
    for sequence in re.findall(r"[\u4e00-\u9fff]+", text):
        result.extend(sequence[i:i + 2] for i in range(len(sequence) - 1))
        if len(sequence) == 1:
            result.append(sequence)
    return result


def split_document(text, source, max_chars=550):
    """Heading/line-aware chunks; oversized single lines retain their line number."""
    lines = text.splitlines()
    pending, start, heading = [], 1, ""

    def chunk(end):
        body = "\n".join(pending).strip()
        if not body:
            return None
        digest = hashlib.sha256(f"{source}:{start}:{end}:{body}".encode()).hexdigest()[:16]
        return {"id": digest, "source": source, "start_line": start,
                "end_line": end, "heading": heading, "text": body}

    for number, line in enumerate(lines, 1):
        if pending and (line.startswith("#") or sum(map(len, pending)) + len(line) > max_chars):
            item = chunk(number - 1)
            if item:
                yield item
            pending = []
        if line.startswith("#"):
            heading = line.lstrip("# ").strip()
        if not pending:
            start = number
        if len(line) > max_chars:
            for offset in range(0, len(line), max_chars):
                pending = [line[offset:offset + max_chars]]
                item = chunk(number)
                if item:
                    yield item
            pending = []
        else:
            pending.append(line)
    if pending:
        item = chunk(len(lines))
        if item:
            yield item


class KnowledgeBase:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY, source TEXT NOT NULL, start_line INTEGER,
                end_line INTEGER, heading TEXT, text TEXT NOT NULL)""")
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(id UNINDEXED, tokens)")

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def index(self, directory):
        root = Path(directory).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("知识库路径必须是目录")
        chunks, files = [], 0
        for path in sorted(root.rglob("*")):
            if path.suffix.lower() not in {".md", ".txt"} or not path.is_file():
                continue
            if not path.resolve().is_relative_to(root):
                raise ValueError("知识库不能通过链接读取目录外的文件")
            if path.stat().st_size > 1024 * 1024:
                raise ValueError(f"文件超过 1 MB：{path.name}")
            source = path.relative_to(root).as_posix()
            chunks.extend(split_document(path.read_text(encoding="utf-8"), source))
            files += 1
        # Build first, then replace atomically. Re-indexing removes obsolete files/chunks.
        with self.connect() as conn:
            conn.execute("DELETE FROM search_index")
            conn.execute("DELETE FROM chunks")
            for item in chunks:
                conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", tuple(item.values()))
                conn.execute("INSERT INTO search_index(id,tokens) VALUES (?,?)",
                             (item["id"], " ".join(tokenize(item["heading"] + " " + item["text"]))))
        return {"files": files, "chunks": len(chunks), "retriever": "sqlite-fts5-bm25-cjk-bigram"}

    def search(self, query, top_k=3):
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            raise ValueError("检索文本需为 1 到 2000 字符")
        if type(top_k) is not int or not 1 <= top_k <= 8:
            raise ValueError("top_k 需为 1 到 8 的整数")
        terms = list(dict.fromkeys(tokenize(query)))[:80]
        if not terms:
            return []
        expression = " OR ".join('"' + term + '"' for term in terms)
        with self.connect() as conn:
            rows = conn.execute("""SELECT chunks.*, bm25(search_index) AS score
                FROM search_index JOIN chunks ON chunks.id=search_index.id
                WHERE search_index MATCH ? ORDER BY score, chunks.id LIMIT ?""", (expression, top_k))
            return [dict(row) for row in rows]

    def count(self):
        with self.connect() as conn:
            return conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
