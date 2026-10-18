
import time
import uuid
import os
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

ALLOWED_ORIGINS = [
    "https://app-v033o4.example.com",
    # Add your actual exam page origin here
    "https://app-h6sqte.example.com",
    "https://exam.sanand.workers.dev",

]

# Request context middleware
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestContextMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins="https://app-v033o4.example.com",
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
    expose_headers=["X-Request-ID"],
)

# Rate limiting: 14 requests per 10 seconds per client
requests_by_client = defaultdict(deque)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/ping" and request.method == "GET":
            client_id = request.headers.get("X-Client-Id", "default")
            now = time.monotonic()
            bucket = requests_by_client[client_id]

            while bucket and now - bucket[0] >= 10:
                bucket.popleft()

            if len(bucket) >= 14:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={
                        "X-Request-ID": getattr(
                            request.state, "request_id", str(uuid.uuid4())
                        )
                    },
                )

            bucket.append(now)

        return await call_next(request)

app.add_middleware(RateLimitMiddleware)

@app.get("/")
async def home():
    return {"message": "Service is running"}
    
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": "23f3003280@ds.study.iitm.ac.in",
        "request_id": request.state.request_id,
    }

@app.options("/ping")
async def ping_options():
    return JSONResponse(content={"ok": True})
