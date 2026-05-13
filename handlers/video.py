from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from utils.logger import get_logger
from config import SUPPORTED_STREAM_PROTOCOLS

logger = get_logger(__name__)

async def play_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Play video in video chat - /play_video <URL>"""
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: /play_video <stream_url>\n"
            "Example: /play_video https://example.com/video.mp4"
        )
        return
    
    url = context.args[0]
    
    # Validate URL
    if not any(url.startswith(proto) for proto in SUPPORTED_STREAM_PROTOCOLS):
        await update.message.reply_text(
            "❌ Invalid URL. Supported protocols: HTTP, HTTPS, RTMP"
        )
        return
    
    try:
        # Get video chat info
        chat = update.effective_chat
        
        if not hasattr(chat, 'video_chat_active'):
            await update.message.reply_text(
                "❌ No active video chat. Please start a video chat first."
            )
            return
        
        await update.message.reply_text(
            f"🎬 Attempting to play video from:\n{url}\n\nPlease wait..."
        )
        
        # Get stream manager from bot_data
        stream_manager = context.bot_data.get('stream_manager')
        if not stream_manager:
            await update.message.reply_text("❌ Stream manager not initialized")
            return
        
        # Create unique stream ID
        stream_id = f"video_{chat.id}_{update.message.message_id}"
        
        # Start the stream
        success = await stream_manager.start_video_stream(
            stream_id=stream_id,
            url=url,
            on_data=lambda sid, data: _send_video_chunk(context, chat.id, sid, data)
        )
        
        if success:
            await update.message.reply_text("✅ Video streaming started!")
            context.chat_data['current_stream'] = stream_id
        else:
            await update.message.reply_text("❌ Failed to start video stream")
            
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")
        await update.message.reply_text(f"❌ Telegram error: {e}")
    except Exception as e:
        logger.error(f"Error playing video: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def play_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Play stream with auto-detection - /play_stream <URL>"""
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: /play_stream <stream_url>\n"
            "Example: /play_stream https://example.com/stream"
        )
        return
    
    url = context.args[0]
    
    # Validate URL
    if not any(url.startswith(proto) for proto in SUPPORTED_STREAM_PROTOCOLS):
        await update.message.reply_text(
            "❌ Invalid URL. Supported protocols: HTTP, HTTPS, RTMP"
        )
        return
    
    try:
        from utils.ffmpeg_utils import FFmpegHandler
        
        # Get stream info
        stream_info = FFmpegHandler.get_stream_info(url)
        
        if not stream_info:
            await update.message.reply_text("⚠️ Could not detect stream type. Attempting as audio...")
            # Default to audio
            await play_video(update, context)
            return
        
        # Auto-detect and play
        # For now, default to video
        await play_video(update, context)
        
    except Exception as e:
        logger.error(f"Error in auto-detect stream: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def _send_video_chunk(context: ContextTypes.DEFAULT_TYPE, 
                           chat_id: int, 
                           stream_id: str, 
                           data: bytes) -> None:
    """Send video chunk to video chat"""
    try:
        # This is where you would send video to the video chat
        # The actual implementation depends on Telegram's video chat API
        pass
    except Exception as e:
        logger.error(f"Error sending video chunk: {e}")
