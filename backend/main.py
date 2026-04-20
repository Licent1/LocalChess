"""FastAPI chess backend (multi-game)

- Supports multiple concurrent games via a generated `game_id`
- Stores game state in-memory (per-process)
- Cleans up stale games after a TTL so memory doesn't grow forever
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Dict, Optional

import chess
import chess.engine
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import engine, Base
from routers import auth

app = FastAPI()

app.include_router(auth.router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Allow frontend to call backend in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stockfish binary path:
# - set STOCKFISH_PATH env var if needed (e.g. /usr/bin/stockfish)
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "stockfish")

# ---- Multi-game state (in-memory) ----
# game_id -> chess board
games: Dict[str, chess.Board] = {}
# game_id -> last activity timestamp
last_seen: Dict[str, float] = {}

GAME_TTL_SECONDS = 6 * 60 * 60  # 6 hours

# Single engine instance shared across games (per process)
engine: Optional[chess.engine.SimpleEngine] = None


def cleanup_games() -> None:
    """Remove stale games so memory doesn't grow forever."""
    now = time.time()
    stale_game_ids = [
        gid for gid, ts in last_seen.items() if (now - ts) > GAME_TTL_SECONDS
    ]
    for gid in stale_game_ids:
        games.pop(gid, None)
        last_seen.pop(gid, None)


# ---- API Models ----
class StartResponse(BaseModel):
    game_id: str
    fen: str


class MoveRequest(BaseModel):
    game_id: str
    move: str  # e.g. "e2e4" or promotion like "e7e8q"


class MoveResponse(BaseModel):
    game_id: str
    fen: str
    player_move: str
    engine_move: str | None
    status: str  # "ok" or result like "1-0", "0-1", "1/2-1/2"


# ---- Lifecycle ----
@app.on_event("startup")
def startup() -> None:
    global engine
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)


@app.on_event("shutdown")
def shutdown() -> None:
    global engine
    if engine is not None:
        engine.quit()
        engine = None


# ---- Routes ----
@app.post("/game/start", response_model=StartResponse)
def game_start() -> StartResponse:
    """Start a new game and return a fresh game_id + initial FEN."""
    cleanup_games()

    game_id = str(uuid.uuid4())
    board = chess.Board()

    games[game_id] = board
    last_seen[game_id] = time.time()

    return StartResponse(game_id=game_id, fen=board.fen())


@app.post("/game/move", response_model=MoveResponse)
def game_move(req: MoveRequest) -> MoveResponse:
    """Apply a player's move, then reply with Stockfish's move (if game not over)."""
    global engine
    cleanup_games()

    board = games.get(req.game_id)
    if board is None:
        raise HTTPException(
            status_code=404, detail="Unknown game_id. Start a new game."
        )

    # Mark game as active
    last_seen[req.game_id] = time.time()

    # Parse move
    try:
        move = chess.Move.from_uci(req.move)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="Bad move format. Use like e2e4 or e7e8q."
        ) from exc

    # Validate legality
    if move not in board.legal_moves:
        raise HTTPException(status_code=400, detail="Illegal move.")

    # Apply player's move
    board.push(move)

    # If game ended after player's move
    if board.is_game_over():
        return MoveResponse(
            game_id=req.game_id,
            fen=board.fen(),
            player_move=req.move,
            engine_move=None,
            status=board.result(),
        )

    if engine is None:
        raise HTTPException(status_code=500, detail="Stockfish engine not started.")

    # Let Stockfish respond quickly
    result = engine.play(board, chess.engine.Limit(time=0.1))
    engine_move = result.move.uci()
    board.push(result.move)

    status = "ok"
    if board.is_game_over():
        status = board.result()

    return MoveResponse(
        game_id=req.game_id,
        fen=board.fen(),
        player_move=req.move,
        engine_move=engine_move,
        status=status,
    )