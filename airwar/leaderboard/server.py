"""FastAPI leaderboard server for local remote-database simulation."""

from __future__ import annotations

import argparse
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from airwar.leaderboard.config import LeaderboardConfig
from airwar.leaderboard.models import (
    LeaderboardRankResponse,
    LeaderboardResponse,
    LeaderboardSubmitRequest,
)
from airwar.leaderboard.store import SQLiteLeaderboardStore

logger = logging.getLogger(__name__)


def create_app(store: SQLiteLeaderboardStore | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        store: Optional store instance. When None, a store is created from
            the environment configuration.

    Returns:
        The configured FastAPI app.
    """
    config = LeaderboardConfig()
    leaderboard_store = store if store is not None else SQLiteLeaderboardStore(config.db_path)

    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        """Log startup info and yield control to the application."""
        logger.info("Leaderboard server ready (DB: %s)", config.db_path)
        yield

    app = FastAPI(title="AirWar Leaderboard", lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        """Return a simple health check."""
        return {"status": "ok"}

    @app.get("/leaderboard", response_model=LeaderboardResponse)
    def get_leaderboard(limit: int = Query(10, ge=1, le=100)) -> LeaderboardResponse:
        """Return the top ``limit`` leaderboard entries."""
        entries = leaderboard_store.get_leaderboard(limit=limit)
        return LeaderboardResponse(entries=entries, total=leaderboard_store.count())

    @app.post("/leaderboard", response_model=LeaderboardRankResponse)
    def submit_score(request: LeaderboardSubmitRequest) -> LeaderboardRankResponse:
        """Submit a new score and return its rank."""
        rank = leaderboard_store.submit_score(
            player_name=request.player_name,
            score=request.score,
        )
        return LeaderboardRankResponse(rank=rank)

    return app


def main() -> None:
    """Command-line entry point for the leaderboard server."""
    parser = argparse.ArgumentParser(description="AirWar leaderboard server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--db-path", default=None, help="SQLite database path")
    args = parser.parse_args()

    if args.db_path:
        os.environ["AIRWAR_LEADERBOARD_DB_PATH"] = args.db_path

    logging.basicConfig(level=logging.INFO)
    uvicorn.run("airwar.leaderboard.server:create_app", host=args.host, port=args.port, factory=True)


if __name__ == "__main__":
    main()
