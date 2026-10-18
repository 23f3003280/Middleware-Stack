
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Your logged-in email
EMAIL = "23f3003450@ds.study.iitm.ac.in"

# Allowed browser origins
ALLOWED_ORIGINS = [
    "https://app-v033o4.example.com",
    "https://app-h6sqte.example.com",
    "https://exam.sanand.workers.dev",
]

# Rate limit: 14 requests per 10 seconds per client
RATE_LIMIT = 14
WINDOW_SECONDS = 10

app = FastAPI()

# Store timestamps separately for each client ID
rate_buckets = defaultdict(deque)
rate_lock = Lock()


@app.middleware("http")
async def request_context_and_rate_limit(
    request: Request, call_next
):
    # Reuse the incoming request ID or generate a new UUID
    request_id = (
        request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )
    request.state.request_id = request_id

    # Rate-limit GET /ping requests
    if (
        request.method == "GET"
        and request.url.path == "/ping"
    ):
        client_id = request.headers.get(
            "X-Client-Id", "anonymous"
        )
        now = time.monotonic()

        with rate_lock:
            bucket = rate_buckets[client_id]

            # Remove timestamps outside the 10-second window
            while (
                bucket
                and now - bucket[0] >= WINDOW_SECONDS
            ):
                bucket.popleft()

            # Reject requests once the bucket is full
            if len(bucket) >= RATE_LIMIT:
                retry_after = max(
                    1,
                    int(
                        WINDOW_SECONDS
                        - (now - bucket[0])
                        + 0.999
                    ),
                )

                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded"
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-Request-ID": request_id,
                    },
                )

            bucket.append(now)

    # Continue to the endpoint
    response = await call_next(request)

    # Return the request ID in the response header
    response.headers["X-Request-ID"] = request_id

    return response


# Optional homepage
@app.get("/")
async def home():
    return {
        "message": "FastAPI service is running",
        "endpoint": "/ping",
    }


# Required endpoint
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }


# CORS middleware: register after the other middleware
# so browser preflight requests are handled correctly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=[
        "X-Request-ID",
        "X-Client-Id",
        "Content-Type",
    ],
    expose_headers=["X-Request-ID"],
    allow_credentials=False,
)
