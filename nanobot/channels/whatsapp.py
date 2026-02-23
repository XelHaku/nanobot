"""WhatsApp channel implementation using Node.js bridge."""

import asyncio
import json
import re

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import WhatsAppConfig


class WhatsAppChannel(BaseChannel):
    """
    WhatsApp channel that connects to a Node.js bridge.
    
    The bridge uses @whiskeysockets/baileys to handle the WhatsApp Web protocol.
    Communication between Python and Node.js is via WebSocket.
    """
    
    name = "whatsapp"
    
    def __init__(self, config: WhatsAppConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: WhatsAppConfig = config
        self._ws = None
        self._connected = False
        self._bot_jid: str = ""

    async def start(self) -> None:
        """Start the WhatsApp channel by connecting to the bridge."""
        import websockets
        
        bridge_url = self.config.bridge_url
        
        logger.info("Connecting to WhatsApp bridge at {}...", bridge_url)
        
        self._running = True
        
        while self._running:
            try:
                async with websockets.connect(bridge_url) as ws:
                    self._ws = ws
                    # Send auth token if configured
                    if self.config.bridge_token:
                        await ws.send(json.dumps({"type": "auth", "token": self.config.bridge_token}))
                    self._connected = True
                    logger.info("Connected to WhatsApp bridge")
                    
                    # Listen for messages
                    async for message in ws:
                        try:
                            await self._handle_bridge_message(message)
                        except Exception as e:
                            logger.error("Error handling bridge message: {}", e)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected = False
                self._ws = None
                logger.warning("WhatsApp bridge connection error: {}", e)
                
                if self._running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
    
    async def stop(self) -> None:
        """Stop the WhatsApp channel."""
        self._running = False
        self._connected = False
        
        if self._ws:
            await self._ws.close()
            self._ws = None
    
    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through WhatsApp."""
        if not self._ws or not self._connected:
            logger.warning("WhatsApp bridge not connected")
            return
        
        try:
            payload = {
                "type": "send",
                "to": msg.chat_id,
                "text": msg.content
            }
            await self._ws.send(json.dumps(payload, ensure_ascii=False))
        except Exception as e:
            logger.error("Error sending WhatsApp message: {}", e)
    
    async def _handle_bridge_message(self, raw: str) -> None:
        """Handle a message from the bridge."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from bridge: {}", raw[:100])
            return
        
        msg_type = data.get("type")
        
        if msg_type == "message":
            pn = data.get("pn", "")
            sender = data.get("sender", "")
            content = data.get("content", "")
            is_group = data.get("isGroup", False)
            participant = data.get("participant", "")
            mentioned_jids: list[str] = data.get("mentionedJids", [])

            # For group messages: use participant (the actual person who sent it)
            # For DMs: use pn (phone-style) if available, else sender (LID-style)
            if is_group and participant:
                user_id = participant
            else:
                user_id = pn if pn else sender

            sender_id = user_id.split("@")[0] if "@" in user_id else user_id
            chat_id = sender  # Group JID for groups, individual JID for DMs

            logger.info("WhatsApp msg from {} (group={}, chat={})", sender_id, is_group, chat_id)

            # Handle voice transcription
            if content == "[Voice Message]":
                logger.info("Voice message from {}, transcription not yet supported.", sender_id)
                content = "[Voice Message: Transcription not available for WhatsApp yet]"

            # Group policy check
            if is_group:
                if not self._should_respond_in_group(content, chat_id, mentioned_jids):
                    logger.debug(
                        "WhatsApp: group message skipped (policy={})",
                        self.config.group_policy,
                    )
                    return
                content = self._strip_mention_keyword(content)

            await self._handle_message(
                sender_id=sender_id,
                chat_id=chat_id,
                content=content,
                metadata={
                    "message_id": data.get("id"),
                    "timestamp": data.get("timestamp"),
                    "is_group": is_group,
                    "participant": participant,
                    "mentioned_jids": mentioned_jids,
                },
            )
        
        elif msg_type == "status":
            status = data.get("status", "")

            # Parse bot JID broadcast (format: "bot_jid:<jid>")
            if isinstance(status, str) and status.startswith("bot_jid:"):
                self._bot_jid = status[len("bot_jid:"):]
                logger.info("WhatsApp bot JID: {}", self._bot_jid)
                return

            logger.info("WhatsApp status: {}", status)

            if status == "connected":
                self._connected = True
            elif status == "disconnected":
                self._connected = False
        
        elif msg_type == "qr":
            # QR code for authentication
            logger.info("Scan QR code in the bridge terminal to connect WhatsApp")
        
        elif msg_type == "error":
            logger.error("WhatsApp bridge error: {}", data.get('error'))

    def _should_respond_in_group(
        self, content: str, group_jid: str, mentioned_jids: list[str]
    ) -> bool:
        """Check if the bot should respond to a group message based on group_policy."""
        policy = self.config.group_policy

        if policy == "ignore":
            return False

        if policy == "open":
            return True

        if policy == "mention":
            # Check native WhatsApp @mention
            if self._bot_jid:
                bot_number = self._bot_jid.split("@")[0].split(":")[0]
                for jid in mentioned_jids:
                    jid_number = jid.split("@")[0].split(":")[0]
                    if bot_number == jid_number:
                        return True

            # Check keyword trigger
            if self.config.mention_keyword:
                if self.config.mention_keyword.lower() in content.lower():
                    return True

            return False

        if policy == "allowlist":
            return group_jid in self.config.group_allow_from

        logger.warning("Unknown WhatsApp group_policy: {}", policy)
        return False

    def _strip_mention_keyword(self, content: str) -> str:
        """Remove the mention keyword from message content."""
        if not self.config.mention_keyword:
            return content

        pattern = re.compile(re.escape(self.config.mention_keyword), re.IGNORECASE)
        cleaned = pattern.sub("", content).strip()
        return cleaned if cleaned else content
