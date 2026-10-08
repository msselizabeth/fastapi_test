# Transcript chunking API

`POST /chunk` splits an English YouTube transcript into semantic chunks.
`GET /` is the health endpoint; `/docs` provides interactive testing.
MiniLM runs locally through FastEmbed. No LLM API, API key, or Pinecone connection.

## Call from Cyclr

Send JSON with `Content-Type: application/json`. Map the source's `fullText`
**string value** into `text`:

```json
{
  "text": "00:00:10.960\nWe create a payment link.\n\n00:00:15.000\nThen we email it.",
  "youtubeLink": "https://www.youtube.com/watch?v=NEvz5xkdUJE",
  "title": "Example video"
}
```

Supported input is a timestamp (`HH:MM:SS.mmm`) on its own line followed by text.
Pass the text value directly, not a JSON-encoded fullText object or WebVTT/SRT ranges.
`youtubeId` is extracted automatically from `youtubeLink`; do not send it in the
request. Watch, youtu.be, shorts, embed, and live video links are supported.
Invalid video links return `422`.

```json
{
  "chunks": [{
    "youtubeId": "NEvz5xkdUJE",
    "chunk_index": 0,
    "start_sec": 10.96,
    "text": "We create a payment link. Then we email it.",
    "youtube_url": "https://www.youtube.com/watch?v=NEvz5xkdUJE",
    "time_youtube_url": "https://www.youtube.com/watch?v=NEvz5xkdUJE&t=10s",
    "title": "Example video"
  }],
  "chunk_count": 1
}
```

Iterate over `chunks` in Cyclr. `start_sec` is the source timestamp of the chunk's
first word. `youtube_url` preserves the supplied link; `time_youtube_url` is a
canonical watch link with the chunk's whole-second start, replacing any original
timestamp or tracking parameters. Timestamps refer to
transcript segments, not exact word times. Text is preserved without rewriting
or deduplication.

## Chunking settings

The algorithm splits text into sentences, embeds them, compares adjacent sentence
similarity, and starts a chunk when similarity drops. Long unpunctuated sentences
are divided into 60-word units. Embeddings are temporary and never returned or saved.

Optional request fields:

| Field | Default | Meaning |
| --- | --- | --- |
| `min_chunk_words` | 60 | Minimum before a topic split (1-500) |
| `max_chunk_words` | 250 | Maximum chunk length (60-1000) |
| `breakpoint_threshold` | 0.5 | Cosine distance (0-2); lower means more splits |

Distance is `1 - similarity`: a similarity threshold of 0.7 means a distance
threshold of 0.3. Minimum must not exceed maximum. Final chunks and forced size
splits can be shorter than the minimum. Word counts are not tokenizer counts.
Topic boundaries and punctuation-based sentence detection are approximate.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download_model.py
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs. Model files are cached in the ignored
`.model_cache` folder. The first inference loads the model into memory.

## Deploy on Render (no YAML)

Push the code to GitHub and connect it to a Render Python Web Service.

Build command:

```sh
pip install -r requirements.txt && python download_model.py
```

Start command:

```sh
uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
```

Use `/` as the health check. Model download requires internet during the build.
Render Free's 512 MB memory limit has not been verified for this app; check
memory usage after deployment. Free instances sleep when idle.
[Render limits](https://render.com/docs/free), [compute plans](https://render.com/docs/compute-plans).

## Files and errors

- `main.py`: endpoints, app setup, validation and unexpected-error handlers.
- `schemas.py`: request, response, and timestamped word classes.
- `chunking.py`: transcript parser, cached model loader, semantic splitter, response assembly.
- `download_model.py`: prepares the model during deployment.
- `test_chunking.py`: parser, semantic splitting, and API tests.

Errors use JSON `detail`: `422` for invalid input, `503` for an unavailable
model, and `500` for unexpected errors (traceback in server logs). Requests are limited to 1,000,000 transcript characters.
Concurrent chunk requests are currently enabled for testing. Only model initialization
is locked, so requests share one model per worker. To restore the previous limit,
uncomment both the `MODEL_LOCK.acquire` block and `MODEL_LOCK.release` in
`create_chunks`. Concurrent inference uses more memory and CPU; local tests do not
guarantee capacity on Render Free. This remains a public test API.

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest -v
```
