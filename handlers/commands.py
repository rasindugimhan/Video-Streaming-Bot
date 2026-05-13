from telegram import Update
from telegram.ext import ContextTypes
from utils.logger import get_logger

logger = get_logger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    welcome_text = """
🎵 Welcome to Telegram Music & Video Bot! 🎬

**Available Commands:**

🎵 Music Commands:
/play_music <URL> - Play music in video chat
/pause - Pause current playback
/resume - Resume playback
/stop - Stop playback

🎬 Video Commands:
/play_video <URL> - Play video in video chat
/play_stream <URL> - Play stream (auto-detect audio/video)

📊 Status:
/status - Show current playback status
/help - Show this help message

**Note:** This bot must have admin rights in the group/channel.
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_text = """
**Bot Features:**

✅ Play audio streams in video chats
✅ Play video streams in video chats  
✅ Pause/Resume/Stop playback
✅ View playback status
✅ Support for HTTP/HTTPS streams
✅ FFmpeg-based conversion

**Supported Formats:**
- Audio: MP3, WAV, M4A, FLAC, AAC
- Video: MP4, MKV, AVI, WEBM, MOV

**Requirements:**
- Bot must be admin in group/channel
- FFmpeg must be installed on the server

**Issues?** Contact the administrator.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command"""
    # This will be updated with actual streaming status
    from utils.streaming import StreamManager
    
    manager = context.bot_data.get('stream_manager')
    if not manager:
        await update.message.reply_text("Stream manager not initialized")
        return
    
    active_streams = manager.list_active_streams()
    if not active_streams:
        await update.message.reply_text("❌ No active streams")
        return
    
    status_text = "📊 **Active Streams:**\n"
    for stream_id in active_streams:
        stream_info = manager.get_stream_status(stream_id)
        if stream_info:
            status = "⏸️ Paused" if stream_info.get('paused') else "▶️ Playing"
            stream_type = stream_info.get('type', 'unknown').upper()
            status_text += f"\n{stream_type}: {status}"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
