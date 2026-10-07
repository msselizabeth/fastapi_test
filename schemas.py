"""Data classes used by the API and transcript chunker."""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator


@dataclass(frozen=True)
class Word:
    text: str
    start: float


class ChunkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=1_000_000)
    youtubeLink: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=1000)
    min_chunk_words: int = Field(default=60, ge=1, le=500, strict=True)
    max_chunk_words: int = Field(default=250, ge=60, le=1000, strict=True)
    breakpoint_threshold: float = Field(default=0.5, ge=0.0, le=2.0)

    @model_validator(mode="after")
    def validate_sizes(self):
        if self.min_chunk_words > self.max_chunk_words:
            raise ValueError("min_chunk_words must not exceed max_chunk_words")
        return self


class Chunk(BaseModel):
    youtubeId: str
    chunk_index: int
    start_sec: float
    text: str
    youtube_url: str
    time_youtube_url: str
    title: str


class ChunkResponse(BaseModel):
    chunks: list[Chunk]
    chunk_count: int
