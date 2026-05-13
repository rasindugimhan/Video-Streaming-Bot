from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from utils.logger import get_logger
from config import SUPPORTED_STREAM_PROTOCOLS

logger = get_logger(__name__)

async def play_music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Play music in video chat - /play_music <URL>"""
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: /play_music <stream_url>\n"
            "Example: /play_music https://example.com/music.mp3"
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
            f"🎵 Attempting to play music from:\n{url}\n\nPlease wait..."
        )
        
        # Get stream manager from bot_data
        stream_manager = context.bot_data.get('stream_manager')
        if not stream_manager:
            await update.message.reply_text("❌ Stream manager not initialized")
            return
        
        # Create unique stream ID
        stream_id = f"audio_{chat.id}_{update.message.message_id}"
        
        # Start the stream
        success = await stream_manager.start_audio_stream(
            stream_id=stream_id,
            url=url,
            on_data=lambda sid, data: _send_audio_chunk(context, chat.id, sid, data)
        )
        
        if success:
            await update.message.reply_text("✅ Music streaming started!")
            context.chat_data['current_stream'] = stream_id
        else:
            await update.message.reply_text("❌ Failed to start music stream")
            
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")
        await update.message.reply_text(f"❌ Telegram error: {e}")
    except Exception as e:
        logger.error(f"Error playing music: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def pause_playback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pause current playback - /pause"""
    try:
        stream_manager = context.bot_data.get('stream_manager')
        current_stream = context.chat_data.get('current_stream')
        
        if not current_stream:
            await update.message.reply_text("❌ No active stream to pause")
            return
        
        if stream_manager.pause_stream(current_stream):
            await update.message.reply_text("⏸️ Playback paused")
        else:
            await update.message.reply_text("❌ Could not pause stream")
            
    except Exception as e:
        logger.error(f"Error pausing playback: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def resume_playback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Resume playback - /resume"""
    try:
        stream_manager = context.bot_data.get('stream_manager')
        current_stream = context.chat_data.get('current_stream')
        
        if not current_stream:
            await update.message.reply_text("❌ No stream to resume")
            return
        
        if stream_manager.resume_stream(current_stream):
            await update.message.reply_text("▶️ Playback resumed")
        else:
            await update.message.reply_text("❌ Could not resume stream")
            
    except Exception as e:
        logger.error(f"Error resuming playback: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def stop_playback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop playback - /stop"""
    try:
        stream_manager = context.bot_data.get('stream_manager')
        current_stream = context.chat_data.get('current_stream')
        
        if not current_stream:
            await update.message.reply_text("❌ No active stream")
            return
        
        if stream_manager.stop_stream(current_stream):
            context.chat_data['current_stream'] = None
            await update.message.reply_text("⏹️ Playback stopped")
        else:
            await update.message.reply_text("❌ Could not stop stream")
            
    except Exception as e:
        logger.error(f"Error stopping playback: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def _send_audio_chunk(context: ContextTypes.DEFAULT_TYPE, 
                           chat_id: int, 
                           stream_id: str, 
                           data: bytes) -> None:
    """Send audio chunk to video chat"""
    try:
        # This is where you would send audio to the video chat
        # The actual implementation depends on Telegram's video chat API
        pass
    except Exception as e:
        logger.error(f"Error sending audio chunk: {e}")
