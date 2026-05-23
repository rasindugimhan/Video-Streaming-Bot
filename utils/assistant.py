import os
import random
import asyncio
from utils.logger import get_logger
from config import API_ID, API_HASH, TEMP_DIR

SESSION_STRING = os.getenv('SESSION_STRING', '')

logger = get_logger(__name__)

# Initialize event loop if not running to prevent Pyrogram import failure on modern Python versions
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Import pyrogram
try:
    import pyrogram
    from pyrogram import Client
    from pyrogram.raw.functions.phone import CreateGroupCall
    from pyrogram.raw.types import InputPeerChannel, InputPeerChat
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False
    logger.warning("Pyrogram is not installed")

# Import pytgcalls
try:
    import pytgcalls
    from pytgcalls import PyTgCalls
    from pytgcalls.types import MediaStream
    PYTGCALLS_AVAILABLE = True
except ImportError:
    PYTGCALLS_AVAILABLE = False
    logger.warning("PyTgCalls is not installed. Voice chat streaming will be disabled.")

class AssistantManager:
    """Manages the Pyrogram Userbot and PyTgCalls streaming integration"""
    
    def __init__(self):
        self.client = None
        self.pytgcalls = None
        self.is_running = False
        
    async def initialize(self) -> bool:
        """Initialize the Pyrogram Client and PyTgCalls"""
        if not PYROGRAM_AVAILABLE:
            logger.error("Cannot initialize Assistant: Pyrogram not available")
            return False
            
        if not API_ID or not API_HASH or API_ID == "your_api_id_here" or API_HASH == "your_api_hash_here":
            logger.warning("API_ID or API_HASH is not configured. Userbot will not start.")
            return False
            
        try:
            logger.info("Initializing Userbot Assistant client...")
            
            if SESSION_STRING:
                # Use StringSession for Railway / cloud deployments (no persistent filesystem)
                logger.info("Using SESSION_STRING from environment variable")
                self.client = Client(
                    name="ewings_user",
                    api_id=int(API_ID),
                    api_hash=API_HASH,
                    session_string=SESSION_STRING
                )
            else:
                # File-based session for local development
                logger.info("Using file-based session (local development mode)")
                self.client = Client(
                    name="ewings_user",
                    api_id=int(API_ID),
                    api_hash=API_HASH,
                    workdir=TEMP_DIR
                )
            
            if PYTGCALLS_AVAILABLE:
                logger.info("Initializing PyTgCalls client...")
                self.pytgcalls = PyTgCalls(self.client)
                
                from pytgcalls import filters
                from pytgcalls.types.stream.stream_ended import StreamEnded
                
                @self.pytgcalls.on_update(filters.stream_end)
                async def on_stream_ended(client, update: StreamEnded):
                    # For video streams, it might trigger twice (audio and video). 
                    # We only trigger the next song when the Audio track finishes to avoid double-skips.
                    if update.stream_type == StreamEnded.Type.AUDIO:
                        asyncio.create_task(self._handle_stream_end(update.chat_id))
            else:
                logger.warning("PyTgCalls is NOT available. Streaming features are disabled, but client will run.")
                
            return True
        except Exception as e:
            logger.error(f"Error initializing Assistant: {e}", exc_info=True)
            return False
            
    async def start(self) -> bool:
        """Start the Assistant Userbot and PyTgCalls"""
        if not self.client:
            logger.error("Assistant Client not initialized")
            return False
            
        try:
            logger.info("Starting Pyrogram Assistant client...")
            await self.client.start()
            
            # Pre-populate Pyrogram peer cache to avoid "Peer id invalid" errors in handle_updates
            logger.info("Pre-populating Pyrogram peer cache...")
            try:
                async for dialog in self.client.get_dialogs(limit=200):
                    pass
                logger.info("Pyrogram peer cache pre-populated successfully")
            except Exception as pe:
                logger.warning(f"Non-fatal error pre-populating peer cache: {pe}")
            
            if self.pytgcalls:
                logger.info("Starting PyTgCalls...")
                await self.pytgcalls.start()
                
            self.is_running = True
            me = await self.client.get_me()
            logger.info(f"Userbot Assistant started successfully as @{me.username} ({me.id})")
            return True
        except Exception as e:
            logger.error(f"Error starting Assistant: {e}", exc_info=True)
            return False
            
    async def stop(self) -> None:
        """Stop Assistant and PyTgCalls"""
        self.is_running = False
        if self.pytgcalls:
            try:
                await self.pytgcalls.stop()
            except Exception as e:
                logger.error(f"Error stopping PyTgCalls: {e}")
                
        if self.client:
            try:
                await self.client.stop()
            except Exception as e:
                logger.error(f"Error stopping Pyrogram: {e}")
                
        logger.info("Userbot Assistant stopped")
        
    async def create_group_call(self, chat_id: int) -> bool:
        """Create a group call (voice/video chat) if not active"""
        if not self.client:
            return False
            
        try:
            peer = await self.client.resolve_peer(chat_id)
            await self.client.invoke(
                CreateGroupCall(
                    peer=peer,
                    random_id=random.randint(10000, 999999)
                )
            )
            logger.info(f"Successfully created a new group call in chat: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating group call in {chat_id}: {e}")
            return False
            
    async def play_stream(self, chat_id: int, stream_url: str, audio_url: str = None, video: bool = False) -> bool:
        """Join group call and play media stream (audio/video)"""
        if not self.pytgcalls:
            logger.error("PyTgCalls is not available. Play stream rejected.")
            return False
            
        try:
            logger.info(f"Checking if group call is active in chat {chat_id}...")
            # First, check if group call exists, if not, create one
            try:
                chat = await self.client.get_chat(chat_id)
                if not getattr(chat, 'group_call_is_active', False):
                    logger.info(f"Group call not active in {chat_id}. Creating new group call...")
                    await self.create_group_call(chat_id)
                else:
                    logger.info(f"Group call already active in {chat_id}.")
            except Exception as ex:
                logger.debug(f"Non-fatal error checking/creating group call: {ex}")
            
            # Now stream!
            from pytgcalls.types import VideoQuality
            
            logger.info(f"Preparing MediaStream object for chat {chat_id}. Video enabled: {video}")
            if video:
                media = MediaStream(
                    stream_url,
                    audio_path=audio_url,
                    video_flags=MediaStream.Flags.REQUIRED,
                    video_parameters=VideoQuality.HD_720p
                )
            else:
                media = MediaStream(
                    stream_url,
                    audio_path=audio_url,
                    video_flags=MediaStream.Flags.IGNORE
                )
                
            # Now let pytgcalls play/join
            try:
                logger.info(f"Calling pytgcalls.play() for chat {chat_id}...")
                await self.pytgcalls.play(chat_id, media)
                logger.info(f"pytgcalls.play() successful for chat {chat_id}")
            except AttributeError:
                # Fallback to join_group_call
                logger.info(f"Calling pytgcalls.join_group_call() for chat {chat_id}...")
                await self.pytgcalls.join_group_call(chat_id, media)
                logger.info(f"pytgcalls.join_group_call() successful for chat {chat_id}")
                
            logger.info(f"Assistant successfully playing stream in {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error streaming in voice chat {chat_id}: {e}", exc_info=True)
            return False
            
    async def pause(self, chat_id: int) -> bool:
        """Pause the current playback in the group call"""
        if not self.pytgcalls:
            return False
        try:
            try:
                await self.pytgcalls.pause_stream(chat_id)
            except AttributeError:
                await self.pytgcalls.pause(chat_id)
            return True
        except Exception as e:
            logger.error(f"Error pausing stream in {chat_id}: {e}")
            return False
            
    async def resume(self, chat_id: int) -> bool:
        """Resume paused playback"""
        if not self.pytgcalls:
            return False
        try:
            try:
                await self.pytgcalls.resume_stream(chat_id)
            except AttributeError:
                await self.pytgcalls.resume(chat_id)
            return True
        except Exception as e:
            logger.error(f"Error resuming stream in {chat_id}: {e}")
            return False
            
    async def stop_stream(self, chat_id: int) -> bool:
        """Stop playback and leave group call"""
        if not self.pytgcalls:
            return False
        try:
            try:
                await self.pytgcalls.leave_group_call(chat_id)
            except AttributeError:
                await self.pytgcalls.stop(chat_id)
            return True
        except Exception as e:
            logger.error(f"Error stopping stream in {chat_id}: {e}")
            return False

    async def _handle_stream_end(self, chat_id: int):
        """Called automatically by PyTgCalls when a stream ends. Plays the next item in the queue."""
        from utils.queue_manager import queue_manager
        
        next_item = queue_manager.next(chat_id)
        
        # Update the original status message UI to show playback ended
        msg = queue_manager.get_status_message(chat_id)
        if msg:
            try:
                # We can't update inline keyboards if the message is too old, but we try
                from telegram import InlineKeyboardMarkup
                await msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup([]))
            except Exception:
                pass

        if next_item:
            logger.info(f"Auto-playing next item in chat {chat_id}: {next_item['title']}")
            if msg:
                try:
                    await msg.edit_text(f"⏭ <b>Auto-playing next:</b> <i>{next_item['title']}</i>", parse_mode='HTML')
                except Exception:
                    pass
            
            url = next_item['url']
            is_video = next_item['video']
            
            from utils.youtube_utils import YouTubeDownloader
            if "youtube.com" in url or "youtu.be" in url:
                video_url, audio_url, _ = await YouTubeDownloader.get_stream_url(url, 'video' if is_video else 'audio')
                if not video_url and is_video:
                    return
                if not audio_url and not is_video:
                    audio_url = video_url # fallback for audio-only from get_stream_url
                
                await self.play_stream(chat_id, video_url or audio_url, audio_url=audio_url, video=is_video)
            else:
                # Direct link or local file
                await self.play_stream(chat_id, url, video=is_video)
        else:
            logger.info(f"Queue empty for chat {chat_id}. Leaving voice chat.")
            await self.stop_stream(chat_id)
            queue_manager.clear(chat_id)
            if msg:
                try:
                    await msg.edit_text("⏹ <b>Queue finished.</b> Left the voice chat.", parse_mode='HTML')
                except Exception:
                    pass
