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

        # User identity
        self._users: dict[str, dict] = {}  # phone_suffix -> user record
        self._permissions: dict[str, dict] = {}  # role -> permissions
        self._groups: dict[str, dict] = {}  # group name -> group info
        self._load_users()

    def _load_users(self) -> None:
        """Load users file if configured."""
        if not self.config.users_file:
            return

        from pathlib import Path
        path = Path(self.config.users_file)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            logger.warning("Users file not found: {}", path)
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._permissions = data.get("permisos", {})
            self._groups = {g["nombre"]: g for g in data.get("grupos", [])}

            for user in data.get("usuarios", []):
                phone = user.get("telefono", "")
                normalized = phone.replace("+", "").replace(" ", "").replace("-", "")
                if len(normalized) >= 10:
                    suffix = normalized[-10:]
                    self._users[suffix] = user
                self._users[normalized] = user

            logger.info("Loaded {} users from {}", len(data.get("usuarios", [])), path)
        except Exception as e:
            logger.error("Failed to load users file: {}", e)

    def _resolve_user(self, sender_id: str) -> dict | None:
        """Resolve a sender_id to a user record."""
        if not self._users:
            return None

        normalized = "".join(c for c in sender_id if c.isdigit())

        if normalized in self._users:
            return self._users[normalized]

        if len(normalized) >= 10:
            suffix = normalized[-10:]
            if suffix in self._users:
                return self._users[suffix]

        return None

    def _get_user_permissions(self, user: dict) -> dict:
        """Get merged permissions for a user based on their roles."""
        roles = user.get("roles", [])
        puede: set[str] = set()
        no_puede: set[str] = set()

        for role in roles:
            perm = self._permissions.get(role, {})
            role_puede = perm.get("puede", [])
            if "*" in role_puede:
                return {"puede": ["*"], "no_puede": []}
            puede.update(role_puede)

        for role in roles:
            perm = self._permissions.get(role, {})
            for item in perm.get("no_puede", []):
                if item not in puede:
                    no_puede.add(item)

        return {"puede": sorted(puede), "no_puede": sorted(no_puede)}

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

            # Resolve user identity
            user_record = self._resolve_user(sender_id)
            user_meta = {}
            if user_record:
                user_perms = self._get_user_permissions(user_record)
                user_meta = {
                    "user_name": user_record.get("nombre", ""),
                    "user_phone": user_record.get("telefono", ""),
                    "user_roles": user_record.get("roles", []),
                    "user_permissions": user_perms,
                    "user_groups": user_record.get("grupos", []),
                }

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
                    **user_meta,
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
