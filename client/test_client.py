"""Simple WebSocket client for manual testing."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import pathlib
import time
from typing import Any

import websockets

DEFAULT_URL = "ws://127.0.0.1:8000/ws"


async def run_client(url: str, text: str, output: pathlib.Path | None, timeout: float) -> None:
    """Connect to the WebSocket service, send text, and store received audio."""

    logger = logging.getLogger("test_client")
    start = time.perf_counter()

    async with websockets.connect(url, ping_interval=None) as websocket:
        await websocket.send(json.dumps({"text": text}))
        logger.info("Sent text payload (%d chars)", len(text))

        message = await asyncio.wait_for(websocket.recv(), timeout=timeout)

        if isinstance(message, str):
            logger.error("Received error frame: %s", message)
            raise SystemExit(1)

        elapsed = time.perf_counter() - start
        logger.info("Received audio payload (%d bytes) in %.2fs", len(message), elapsed)

        if output:
            output.write_bytes(message)
            logger.info("Audio written to %s", output)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test client for the LLM→TTS WebSocket service.")
    parser.add_argument("--url", default=DEFAULT_URL, help="WebSocket URL (default: %(default)s)")
    parser.add_argument("--text", required=True, help="Input text to convert.")
    parser.add_argument("--save", type=pathlib.Path, help="Optional output file (mp3).")
    parser.add_argument(
        "--timeout", type=float, default=60.0, help="Seconds to wait for synthesis to complete."
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    try:
        asyncio.run(run_client(args.url, args.text, args.save, args.timeout))
    except KeyboardInterrupt:  # pragma: no cover - manual usage only
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
