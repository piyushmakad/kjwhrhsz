"""Composition root: HTTP middleware and routes only."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app = FastAPI(title="Wind Decision Replay API", version="0.2.0")
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if os.getenv("FRONTEND_ORIGIN"):
    origins.append(os.environ["FRONTEND_ORIGIN"].rstrip("/"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(router)
