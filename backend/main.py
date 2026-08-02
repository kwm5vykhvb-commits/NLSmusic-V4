import asyncio
import hashlib
import io
import json
import math
import os
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeAudio

DB_PATH = "nls_cache.db"
CHANNEL_HANDLE = "@NLS_music"
ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php"
ARCHIVE_METADATA = "https://archive.org/metadata/{identifier}"
MEDIA_CACHE_DIR = Path(os.getenv("MEDIA_CACHE_DIR", "media_cache"))
PAGE_SIZE = 100


@dataclass
class Track:
    id: str
    source: str
    title: str
    artist: str
    duration: str


app = FastAPI(title="NLSmusic API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(db_conn()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cloud_tracks (
                message_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT NOT NULL,
                duration TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS downloads (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _extract_audio_fields(message: Any) -> tuple[str, str, str] | None:
    if not message or not message.media:
        return None

    title = "Unknown Title"
    artist = "Unknown Artist"
    duration_seconds = 0

    audio = getattr(message, "audio", None)
    document = getattr(message, "document", None)
    voice = getattr(message, "voice", None)

    if not any([audio, document, voice]):
        return None

    attrs = []
    if audio and getattr(audio, "attributes", None):
        attrs = audio.attributes
    elif document and getattr(document, "attributes", None):
        attrs = document.attributes

    for attr in attrs:
        if isinstance(attr, DocumentAttributeAudio):
            title = attr.title or title
            artist = attr.performer or artist
            duration_seconds = attr.duration or duration_seconds

    if title == "Unknown Title" and message.file and message.file.name:
        title = message.file.name.rsplit(".", 1)[0]

    duration = f"{duration_seconds // 60}:{duration_seconds % 60:02d}"
    return title, artist, duration


class NLSCloud:
    def __init__(self) -> None:
        self.api_id = os.getenv("API_ID")
        self.api_hash = os.getenv("API_HASH")
        self.bot_token = os.getenv("BOT_TOKEN")

    def _client(self) -> TelegramClient:
        if not self.bot_token:
            raise HTTPException(status_code=500, detail="Error: Check BOT_TOKEN in environment variables")
        if not self.api_id or not self.api_hash:
            raise HTTPException(status_code=500, detail="Error: Missing API_ID or API_HASH in environment variables")

        return TelegramClient("nlsmusic_session", int(self.api_id), self.api_hash)

    async def scan_and_cache(self) -> None:
        with closing(db_conn()) as conn:
            existing = conn.execute("SELECT COUNT(1) AS count FROM cloud_tracks").fetchone()["count"]
        if existing > 0:
            return

        async with self._client() as client:
            await client.start(bot_token=self.bot_token)
            channel = await client.get_entity(CHANNEL_HANDLE)
            offset_id = 0

            while True:
                batch = []
                async for message in client.iter_messages(channel, limit=100, offset_id=offset_id):
                    batch.append(message)

                if not batch:
                    break

                rows = []
                for message in batch:
                    extracted = _extract_audio_fields(message)
                    if not extracted:
                        continue
                    title, artist, duration = extracted
                    rows.append((message.id, title, artist, duration))

                if rows:
                    with closing(db_conn()) as conn:
                        conn.executemany(
                            "INSERT OR IGNORE INTO cloud_tracks(message_id, title, artist, duration) VALUES (?, ?, ?, ?)",
                            rows,
                        )
                        conn.commit()

                offset_id = min(msg.id for msg in batch)
                await asyncio.sleep(2)

    async def search(self, query: str, page: int, tab: str) -> tuple[list[Track], int]:
        await self.scan_and_cache()
        offset = (page - 1) * PAGE_SIZE
        where = "(title LIKE ? OR artist LIKE ?)"
        match_params: list[Any] = [f"%{query}%", f"%{query}%"]

        if tab == "songs":
            where = "title LIKE ?"
            match_params = [f"%{query}%"]
        elif tab == "artists":
            where = "artist LIKE ?"
            match_params = [f"%{query}%"]

        with closing(db_conn()) as conn:
            total = conn.execute(
                f"SELECT COUNT(1) AS count FROM cloud_tracks WHERE {where}", match_params
            ).fetchone()["count"]
            rows = conn.execute(
                f"SELECT message_id, title, artist, duration FROM cloud_tracks WHERE {where} LIMIT ? OFFSET ?",
                [*match_params, PAGE_SIZE, offset],
            ).fetchall()

        tracks = [
            Track(id=f"cloud:{row['message_id']}", source="NLS Cloud", title=row["title"], artist=row["artist"], duration=row["duration"])
            for row in rows
        ]
        return tracks, total

    async def suggestions(self, query: str) -> dict[str, list[str]]:
        await self.scan_and_cache()
        with closing(db_conn()) as conn:
            song_rows = conn.execute(
                "SELECT DISTINCT title FROM cloud_tracks WHERE title LIKE ? LIMIT 5", (f"%{query}%",)
            ).fetchall()
            artist_rows = conn.execute(
                "SELECT DISTINCT artist FROM cloud_tracks WHERE artist LIKE ? LIMIT 5", (f"%{query}%",)
            ).fetchall()

        return {
            "songs": [row["title"] for row in song_rows],
            "artists": [row["artist"] for row in artist_rows],
        }

    async def download(self, message_id: int) -> tuple[bytes, str, str]:
        async with self._client() as client:
            await client.start(bot_token=self.bot_token)
            channel = await client.get_entity(CHANNEL_HANDLE)
            message = await client.get_messages(channel, ids=message_id)
            if not message:
                raise HTTPException(status_code=404, detail="Track not found")

            extracted = _extract_audio_fields(message)
            title, artist, _ = extracted or ("Song", "Artist", "0:00")
            output = io.BytesIO()
            await client.download_media(message, file=output)
            output.seek(0)

        return output.read(), title, artist


nls_cloud = NLSCloud()


async def search_archives(query: str, page: int) -> tuple[list[Track], int]:
    params = {
        "q": query,
        "fl[]": ["identifier", "title", "creator", "duration"],
        "output": "json",
        "rows": PAGE_SIZE,
        "page": page,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(ARCHIVE_SEARCH, params=params, timeout=30) as response:
            if response.status != 200:
                return [], 0
            payload = await response.json()

    response_payload = payload.get("response", {})
    docs = response_payload.get("docs", [])
    total = response_payload.get("numFound", 0)
    results = []
    for doc in docs:
        identifier = doc.get("identifier")
        if not identifier:
            continue
        results.append(
            Track(
                id=f"archive:{identifier}",
                source="NLS Archives",
                title=doc.get("title") or "Unknown Title",
                artist=doc.get("creator") or "Unknown Artist",
                duration=str(doc.get("duration") or "0:00"),
            )
        )
    return results, total


async def download_from_archive(identifier: str) -> tuple[bytes, str, str]:
    async with aiohttp.ClientSession() as session:
        async with session.get(ARCHIVE_METADATA.format(identifier=identifier), timeout=30) as response:
            if response.status != 200:
                raise HTTPException(status_code=404, detail="Track not found")
            payload = await response.json()

        files = payload.get("files", [])
        audio_file = next((f for f in files if str(f.get("name", "")).lower().endswith(".mp3")), None)
        if not audio_file:
            raise HTTPException(status_code=404, detail="No MP3 file found")

        url = f"https://archive.org/download/{identifier}/{audio_file['name']}"
        async with session.get(url, timeout=60) as response:
            if response.status != 200:
                raise HTTPException(status_code=404, detail="Unable to download file")
            data = await response.read()

    title = payload.get("metadata", {}).get("title") or "Song"
    artist = payload.get("metadata", {}).get("creator") or "Artist"
    return data, str(title), str(artist)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_paths(track_id: str) -> tuple[Path, Path]:
    """Build cache file paths from a hash of track_id so no user input reaches the filesystem path."""
    digest = hashlib.sha256(track_id.encode("utf-8")).hexdigest()
    cache_root = MEDIA_CACHE_DIR.resolve()
    audio_path = (cache_root / f"{digest}.mp3").resolve()
    meta_path = (cache_root / f"{digest}.json").resolve()
    if cache_root not in (audio_path, *audio_path.parents) or cache_root not in (meta_path, *meta_path.parents):
        raise HTTPException(status_code=400, detail="Invalid track id")
    return audio_path, meta_path


async def _fetch_audio(track_id: str) -> tuple[bytes, str, str]:
    """Fetch the full mp3 for a track, caching it on disk after the first download."""
    audio_path, meta_path = _cache_paths(track_id)
    if audio_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return audio_path.read_bytes(), meta["title"], meta["artist"]

    source, _, source_id = track_id.partition(":")
    if source == "cloud":
        data, title, artist = await nls_cloud.download(int(source_id))
    elif source == "archive":
        data, title, artist = await download_from_archive(source_id)
    else:
        raise HTTPException(status_code=400, detail="Unsupported source")

    MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(data)
    meta_path.write_text(json.dumps({"title": title, "artist": artist}), encoding="utf-8")
    return data, title, artist


@app.get("/api/search")
async def search(query: str = Query(min_length=1), page: int = 1, tab: str = "all") -> dict[str, Any]:
    cloud_results, cloud_total = await nls_cloud.search(query, page, tab)
    archive_results: list[Track] = []
    archive_total = 0
    if len(cloud_results) < 10:
        archive_results, archive_total = await search_archives(query, page)

    total = cloud_total + archive_total
    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    return {
        "cloud": [track.__dict__ for track in cloud_results],
        "archives": [track.__dict__ for track in archive_results],
        "page": page,
        "total": total,
        "totalPages": total_pages,
    }


@app.get("/api/suggestions")
async def suggestions(query: str = Query(min_length=1)) -> dict[str, Any]:
    return await nls_cloud.suggestions(query)


@app.get("/api/download/{track_id}")
async def download(track_id: str):
    data, title, artist = await _fetch_audio(track_id)
    save_source = "NLS Cloud" if track_id.startswith("cloud:") else "NLS Archives"

    with closing(db_conn()) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO downloads(id, title, artist, source) VALUES (?, ?, ?, ?)",
            (track_id, title, artist, save_source),
        )
        conn.commit()

    filename = f'{title} - {artist}.mp3'.replace('"', "")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/stream/{track_id}")
async def stream(track_id: str, request: Request):
    data, title, artist = await _fetch_audio(track_id)
    total = len(data)
    filename = f'{title} - {artist}.mp3'.replace('"', "")
    range_header = request.headers.get("range")

    if range_header:
        match = re.match(r"bytes=(\d*)-(\d*)", range_header)
        if not match or (not match.group(1) and not match.group(2)):
            raise HTTPException(status_code=416, detail="Invalid Range header")

        start = int(match.group(1)) if match.group(1) else 0
        end = int(match.group(2)) if match.group(2) else total - 1
        end = min(end, total - 1)

        if start > end or start >= total:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{total}"})

        chunk = data[start : end + 1]
        headers = {
            "Content-Range": f"bytes {start}-{end}/{total}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(chunk)),
            "Content-Disposition": f'inline; filename="{filename}"',
        }
        return Response(content=chunk, status_code=206, media_type="audio/mpeg", headers=headers)

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(total),
        "Content-Disposition": f'inline; filename="{filename}"',
    }
    return Response(content=data, media_type="audio/mpeg", headers=headers)


@app.get("/api/downloads")
async def downloads() -> dict[str, Any]:
    with closing(db_conn()) as conn:
        rows = conn.execute("SELECT id, title, artist, source FROM downloads ORDER BY rowid DESC").fetchall()
    return {"items": [dict(row) for row in rows]}

