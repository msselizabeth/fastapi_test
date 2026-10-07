"""Parse simple timestamped transcripts and split them by semantic similarity."""

import logging
from pathlib import Path
import re
from threading import Lock
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException

from schemas import ChunkRequest, ChunkResponse, Word

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_LOCK = Lock()
_model = None
TIMESTAMP = re.compile(r"^[ \t]*(\d{2,}:[0-5]\d:[0-5]\d\.\d{3})[ \t]*$", re.MULTILINE)


def extract_youtube_id(link: str) -> str:
    url = urlparse(link)
    host = (url.hostname or "").lower()
    parts = url.path.strip("/").split("/")
    video_id = ""
    if url.scheme in {"http", "https"}:
        if host == "youtu.be" and len(parts) == 1:
            video_id = parts[0]
        elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
            if url.path == "/watch":
                video_id = parse_qs(url.query).get("v", [""])[0]
            elif len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
                video_id = parts[1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("youtubeLink must be a valid YouTube video URL.")
    return video_id


def parse_transcript(text: str) -> list[Word]:
    """Read HH:MM:SS.mmm lines followed by text; preserve every transcript word."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    cues = list(TIMESTAMP.finditer(text))
    if not cues or cues[0].start() != 0:
        raise ValueError("text must start with a timestamp such as 00:00:10.960 on its own line.")
    times = []
    for cue in cues:
        hours, minutes, seconds = cue[1].split(":")
        times.append(round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3))
    if times != sorted(times):
        raise ValueError("Transcript timestamps must be in chronological order.")

    words = []
    for i, cue in enumerate(cues):
        stop = cues[i + 1].start() if i + 1 < len(cues) else len(text)
        body = text[cue.end():stop].strip()
        if not body or re.search(r"(?m)^\s*\d+:\d", body):
            raise ValueError("Each timestamp must be followed by text. Use HH:MM:SS.mmm timestamps.")
        words.extend(Word(token, times[i]) for token in body.split())
    return words


def load_model():
    """Load one cached CPU model; called while MODEL_LOCK is held."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=str(Path(__file__).resolve().parent / ".model_cache"),
            threads=1,
            providers=["CPUExecutionProvider"],
        )
    return _model


def get_semantic_chunks(words: list[Word], min_words: int = 60,
                        max_words: int = 250, threshold: float = 0.5) -> list[list[Word]]:
    """Split when adjacent sentences differ, retaining their timestamped words."""
    sentences, current = [], []
    for word in words:
        current.append(word)
        # Cap unpunctuated sentences so they fit the embedding model.
        if len(current) == 60 or re.search(r'[.!?]["\u201d\u2019\')]*$', word.text):
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    if len(sentences) < 2:
        return sentences

    import numpy as np

    embeddings = np.asarray(list(load_model().embed(
        [" ".join(word.text for word in sentence) for sentence in sentences], batch_size=4
    )))
    embeddings /= np.maximum(np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-12)
    similarities = np.sum(embeddings[:-1] * embeddings[1:], axis=1)

    chunks, current = [], sentences[0].copy()
    for similarity, sentence in zip(similarities, sentences[1:]):
        topic_change = 1 - float(similarity) >= threshold and len(current) >= min_words
        if topic_change or len(current) + len(sentence) > max_words:
            chunks.append(current)
            current = []
        current.extend(sentence)
    chunks.append(current)
    return chunks


def create_chunks(request: ChunkRequest) -> ChunkResponse:
    if not MODEL_LOCK.acquire(blocking=False):
        raise HTTPException(503, "Chunker is busy. Retry shortly.", headers={"Retry-After": "5"})
    try:
        try:
            youtube_id = extract_youtube_id(request.youtubeLink)
            words = parse_transcript(request.text)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        try:
            groups = get_semantic_chunks(words, request.min_chunk_words,
                                         request.max_chunk_words, request.breakpoint_threshold)
        except Exception as exc:
            logging.exception("Semantic chunking failed")
            raise HTTPException(503, "Semantic model unavailable. Check server logs.") from exc
        chunks = [{
            "youtubeId": youtube_id,
            "chunk_index": index,
            "start_sec": group[0].start,
            "text": " ".join(word.text for word in group),
            "youtube_url": request.youtubeLink,
            "time_youtube_url": f"https://www.youtube.com/watch?v={youtube_id}&t={int(group[0].start)}s",
            "title": request.title,
        } for index, group in enumerate(groups)]
        return ChunkResponse(chunks=chunks, chunk_count=len(chunks))
    finally:
        MODEL_LOCK.release()
