import { useEffect, useMemo, useState } from "react";
import { Chess } from "chess.js";
import { Chessboard } from "react-chessboard";

import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

/**
 * WebSchach MVP Frontend
 * - Starts a new backend game on load (and on Reset)
 * - Sends moves in UCI (e.g. e2e4, e7e8q)
 * - Displays backend FEN after each move (engine responds)
 */
export default function App() {
  // Keep a single Chess() instance for local (UI) move validation
  const game = useMemo(() => new Chess(), []);

  const [fen, setFen] = useState(game.fen());
  const [status, setStatus] = useState("Starting...");
  const [gameId, setGameId] = useState(null);

  async function startNewGame() {
    setStatus("Starting a new game...");

    const res = await fetch(`${API_BASE_URL}/game/start`, { method: "POST" });
    if (!res.ok) {
      setStatus("❌ Failed to start game (backend not reachable).");
      return;
    }

    const data = await res.json();

    setGameId(data.game_id);
    game.load(data.fen);
    setFen(game.fen());

    setStatus("Your move (White)");
  }

  async function sendMove(moveUci) {
    if (!gameId) {
      setStatus("❌ No game_id yet. Press Start / Reset.");
      return;
    }

    const res = await fetch(`${API_BASE_URL}/game/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ game_id: gameId, move: moveUci }),
    });

    if (!res.ok) {
      // Backend rejected the move or state got out of sync:
      // show error and re-sync by starting a new game.
      let detail = "Unknown error";
      try {
        const err = await res.json();
        detail = err?.detail ?? detail;
      } catch {
        // ignore JSON parse errors
      }
      setStatus(`❌ ${detail} (resetting)`);
      await startNewGame();
      return;
    }

    const data = await res.json();

    // Keep game_id in sync (harmless even if unchanged)
    setGameId(data.game_id);

    // Sync local UI board to backend
    game.load(data.fen);
    setFen(game.fen());

    if (data.status !== "ok") {
      setStatus(`Game ended: ${data.status}`);
      return;
    }

    setStatus(`You: ${data.player_move} | Stockfish: ${data.engine_move}`);
  }

  /**
   * react-chessboard handler
   * Some versions call onPieceDrop(sourceSquare, targetSquare, piece),
   * some call it with a single object argument.
   * This wrapper supports the object signature you used.
   */
  function handlePieceDrop({ sourceSquare, targetSquare, piece }) {
    // Auto-queen promotion (MVP)
    const pieceStr =
      typeof piece === "string"
        ? piece
        : piece?.piece || piece?.id || piece?.type || "";

    const isPawn = String(pieceStr).toLowerCase().endsWith("p");
    const isPromotionSquare =
      targetSquare.endsWith("8") || targetSquare.endsWith("1");

    const promotion = isPawn && isPromotionSquare ? "q" : undefined;

    // Apply locally so the UI updates immediately
    const localMove = game.move({
      from: sourceSquare,
      to: targetSquare,
      promotion,
    });

    if (localMove === null) return false;

    setFen(game.fen());

    const moveUci = `${sourceSquare}${targetSquare}${promotion ?? ""}`;
    setStatus(`Sending ${moveUci}...`);
    sendMove(moveUci);

    return true;
  }

  useEffect(() => {
    startNewGame();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="app">
      <header className="header">
        <h2 className="title">WebSchach MVP (Local / School)</h2>

        <div className="controls">
          <button type="button" onClick={startNewGame}>
            Start / Reset
          </button>
        </div>

        <div className="status">
          <span>{status}</span>
          {gameId ? (
            <span className="gameId">game_id: {gameId.slice(0, 8)}…</span>
          ) : null}
        </div>
      </header>

      <main className="boardWrap">
        <Chessboard
          options={{
            id: "board-1",
            position: fen,
            arePiecesDraggable: true,
            onPieceDrop: handlePieceDrop,
          }}
        />
      </main>

      <footer className="footer">
        Local, privacy-friendly chess platform for schools.
      </footer>
    </div>
  );
}
