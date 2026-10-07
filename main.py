"""API setup, error handlers, and endpoints."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from chunking import create_chunks
from schemas import ChunkRequest, ChunkResponse

logger = logging.getLogger(__name__)
app = FastAPI(title="Test API")

# Allow the public test API to be called from any website.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # Keep useful field errors without echoing a potentially large transcript.
    errors = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled error on %s %s", request.method, request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
        # Unhandled errors are processed outside the normal CORS middleware.
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "message": "Hello from FastAPI!"}


@app.post("/chunk", response_model=ChunkResponse)
def chunk_transcript(request: ChunkRequest) -> ChunkResponse:
    """Split timestamped captions using local semantic similarity."""
    return create_chunks(request)
