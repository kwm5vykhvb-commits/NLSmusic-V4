import asyncio
import io
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import Any

import aiohttp
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeAudio

DB_PATH = "nls_cache.db"
CHANNEL_HANDLE = "@NLS_music"
ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php"
ARCHIVE_METADATA = "https://archive.org/metadata/{identifier}"


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

    async def search(self, query: str, page: int, tab: str) -> list[Track]:
        await self.scan_and_cache()
        offset = (page - 1) * 100
        where = "(title LIKE ? OR artist LIKE ?)"
        params: list[Any] = [f"%{query}%", f"%{query}%", 100, offset]

        if tab == "songs":
            where = "title LIKE ?"
            params = [f"%{query}%", 100, offset]
        elif tab == "artists":
            where = "artist LIKE ?"
            params = [f"%{query}%", 100, offset]

        with closing(db_conn()) as conn:
            rows = conn.execute(
                f"SELECT message_id, title, artist, duration FROM cloud_tracks WHERE {where} LIMIT ? OFFSET ?",
                params,
            ).fetchall()

        return [Track(id=f"cloud:{row['message_id']}", source="NLS Cloud", title=row["title"], artist=row["artist"], duration=row["duration"]) for row in rows]

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


async def search_archives(query: str, page: int) -> list[Track]:
    params = {
        "q": query,
        "fl[]": ["identifier", "title", "creator", "duration"],
        "output": "json",
        "rows": 100,
        "page": page,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(ARCHIVE_SEARCH, params=params, timeout=30) as response:
            if response.status != 200:
                return []
            payload = await response.json()

    docs = payload.get("response", {}).get("docs", [])
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
    return results


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


@app.get("/api/search")
async def search(query: str = Query(min_length=1), page: int = 1, tab: str = "all") -> dict[str, Any]:
    cloud_results = await nls_cloud.search(query, page, tab)
    archive_results: list[Track] = []
    if len(cloud_results) < 10:
        archive_results = await search_archives(query, page)

    return {
        "cloud": [track.__dict__ for track in cloud_results],
        "archives": [track.__dict__ for track in archive_results],
        "page": page,
    }


@app.get("/api/suggestions")
async def suggestions(query: str = Query(min_length=1)) -> dict[str, Any]:
    return await nls_cloud.suggestions(query)


@app.get("/api/download/{track_id}")
async def download(track_id: str):
    source, _, source_id = track_id.partition(":")

    if source == "cloud":
        data, title, artist = await nls_cloud.download(int(source_id))
        save_source = "NLS Cloud"
    elif source == "archive":
        data, title, artist = await download_from_archive(source_id)
        save_source = "NLS Archives"
    else:
        raise HTTPException(status_code=400, detail="Unsupported source")

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


@app.get("/api/downloads")
async def downloads() -> dict[str, Any]:
    with closing(db_conn()) as conn:
        rows = conn.execute("SELECT id, title, artist, source FROM downloads ORDER BY rowid DESC").fetchall()
    return {"items": [dict(row) for row in rows]}
