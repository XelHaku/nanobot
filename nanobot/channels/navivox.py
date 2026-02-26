"""NaviVox voice channel (WebSocket audio streaming)."""

from __future__ import annotations

import asyncio
import base64
import json
import os
from datetime import datetime
from pathlib import Path

import websockets
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import NaviVoxConfig
from nanobot.utils.helpers import get_data_path


class NaviVoxChannel(BaseChannel):
    """
    NaviVox voice channel.

    Hosts a WebSocket server with Ed25519 device authentication.
    """

    name = "navivox"

    def __init__(self, config: NaviVoxConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: NaviVoxConfig = config
        self._server: websockets.server.Serve | None = None

    async def start(self) -> None:
        """Start the channel and WebSocket server."""
        self._running = True

        self._server = await websockets.serve(
            self._handle_ws,
            self.config.host,
            self.config.port,
            max_size=4 * 1024 * 1024,
        )
        logger.info("NaviVox WS listening on ws://{}:{}", self.config.host, self.config.port)

        # Keep the channel alive until stop() is called.
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop the channel."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("NaviVox channel stopped")

    async def send(self, msg: OutboundMessage) -> None:
        """Outbound send placeholder (voice streaming not wired yet)."""
        logger.warning("NaviVox send called, but streaming is not implemented yet")

    def _allowed_devices(self) -> dict[str, str]:
        """Return allowlist device_id -> public_key."""
        allowed: dict[str, str] = {}
        for device in self.config.allowed_devices:
            if device.device_id and device.public_key:
                allowed[device.device_id] = device.public_key
        return allowed

    @staticmethod
    def _decode_b64(data: str) -> bytes:
        return base64.b64decode(data.encode("utf-8"), validate=True)

    async def _handle_ws(self, ws: websockets.WebSocketServerProtocol) -> None:
        """Handle a single websocket connection with Ed25519 auth handshake."""
        peer = ws.remote_address[0] if ws.remote_address else "unknown"
        device_id = ""
        pubkey_b64 = ""

        try:
            hello_raw = await asyncio.wait_for(ws.recv(), timeout=5)
            if not isinstance(hello_raw, str):
                await self._deny(ws, peer, device_id, pubkey_b64, "invalid_hello")
                return
            hello = json.loads(hello_raw)
            if hello.get("type") != "hello":
                await self._deny(ws, peer, device_id, pubkey_b64, "invalid_hello")
                return

            device_id = str(hello.get("device_id") or "").strip()
            pubkey_b64 = str(hello.get("pubkey") or "").strip()

            allowed = self._allowed_devices()
            allowed_pubkey = allowed.get(device_id)
            if not device_id or not pubkey_b64 or not allowed_pubkey:
                await self._deny(ws, peer, device_id, pubkey_b64, "not_allowed")
                return
            if pubkey_b64 != allowed_pubkey:
                await self._deny(ws, peer, device_id, pubkey_b64, "pubkey_mismatch")
                return

            nonce = os.urandom(32)
            await ws.send(json.dumps({"type": "challenge", "nonce": base64.b64encode(nonce).decode()}))

            auth_raw = await asyncio.wait_for(ws.recv(), timeout=5)
            if not isinstance(auth_raw, str):
                await self._deny(ws, peer, device_id, pubkey_b64, "invalid_auth")
                return
            auth = json.loads(auth_raw)
            if auth.get("type") != "auth" or "signature" not in auth:
                await self._deny(ws, peer, device_id, pubkey_b64, "invalid_auth")
                return

            try:
                signature = self._decode_b64(str(auth.get("signature")))
                pubkey = self._decode_b64(pubkey_b64)
                Ed25519PublicKey.from_public_bytes(pubkey).verify(signature, nonce)
            except (ValueError, InvalidSignature):
                await self._deny(ws, peer, device_id, pubkey_b64, "bad_signature")
                return

            await ws.send(json.dumps({"type": "ok"}))
            self._log_attempt(peer, device_id, pubkey_b64, "ok")
            logger.info("NaviVox authorized device {} from {}", device_id, peer)

            async for message in ws:
                # Placeholder: accept audio chunks or metadata frames.
                if isinstance(message, str):
                    try:
                        payload = json.loads(message)
                    except json.JSONDecodeError:
                        continue
                    if payload.get("type") == "ping":
                        await ws.send(json.dumps({"type": "pong"}))
                # Binary frames (audio) are ignored for now.
        except asyncio.TimeoutError:
            await self._deny(ws, peer, device_id, pubkey_b64, "timeout")
        except websockets.ConnectionClosed:
            return
        except Exception as e:
            logger.exception("NaviVox WS error: {}", e)
            await self._deny(ws, peer, device_id, pubkey_b64, "error")

    async def _deny(self, ws: websockets.WebSocketServerProtocol, peer: str,
                   device_id: str, pubkey_b64: str, reason: str) -> None:
        self._log_attempt(peer, device_id, pubkey_b64, f"deny:{reason}")
        try:
            await ws.close(code=4003, reason=reason)
        except Exception:
            pass

    def _log_attempt(self, peer: str, device_id: str, pubkey_b64: str, status: str) -> None:
        path = self._attempts_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "remote": peer,
            "device_id": device_id,
            "pubkey": pubkey_b64,
            "status": status,
        }
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("Failed to write NaviVox attempts log")

    @staticmethod
    def _attempts_log_path() -> Path:
        return get_data_path() / "navivox" / "attempts.jsonl"
