import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from utils.logger import get_logger
from utils.youtube_utils import YouTubeDownloader
from utils.assistant import PYTGCALLS_AVAILABLE
from config import SUPPORTED_STREAM_PROTOCOLS, TEMP_DIR

logger = get_logger(__name__)

from utils.queue_manager import queue_manager
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_player_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause", callback_data="cb_pause"),
            InlineKeyboardButton("▶️ Resume", callback_data="cb_resume")
        ],
        [
            InlineKeyboardButton("⏮ Prev", callback_data="cb_prev"),
            InlineKeyboardButton("⏭ Next", callback_data="cb_next")
        ],
        [
            InlineKeyboardButton("⏹ Stop", callback_data="cb_stop"),
            InlineKeyboardButton("🔄 Refresh", callback_data="cb_refresh")
        ],
        [
            InlineKeyboardButton("📋 Queue", callback_data="cb_queue")
        ]
    ])

async def play_music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Play music in video chat - /play <URL> or reply to file"""
    
    # Check if assistant is initialized and running
    assistant = context.bot_data.get('assistant')
    if not assistant or not assistant.client:
        await update.message.reply_html("⚠️ <b>Assistant Not Configured</b>")
        return
        
    if not PYTGCALLS_AVAILABLE:
        await update.message.reply_html("⚠️ <b>Voice Chat Streaming Disabled</b>")
        return
        
    chat_id = update.effective_chat.id
    status_msg = await update.message.reply_html("🔍 <i>Processing request...</i>")
    
    # Check for replied file
    replied = update.message.reply_to_message
    if replied and (replied.audio or replied.voice or replied.document or replied.video):
        await status_msg.edit_text("📥 <i>Downloading file to server...</i>", parse_mode='HTML')
        file_obj = replied.audio or replied.voice or replied.video or replied.document
        
        file_ext = ".mp3"
        if replied.video: file_ext = ".mp4"
        elif getattr(replied.document, 'file_name', None):
            _, file_ext = os.path.splitext(replied.document.file_name)
            
        file_path = os.path.join(TEMP_DIR, f"dl_{file_obj.file_id}{file_ext}")
        
        if not os.path.exists(file_path):
            new_file = await context.bot.get_file(file_obj.file_id)
            await new_file.download_to_drive(file_path)
            
        title = getattr(file_obj, 'title', getattr(file_obj, 'file_name', 'Local File'))
        
        queue_len = queue_manager.add(chat_id, {
            'url': file_path,
            'title': title,
            'video': False,
            'requester': update.effective_user.first_name
        })
        
        if queue_len == 1:
            await _start_playing_current(chat_id, assistant, status_msg)
        else:
            await status_msg.edit_text(f"✅ <b>Added to queue:</b> <i>{title}</i> (Position: {queue_len})", parse_mode='HTML')
        return

    if not context.args or len(context.args) < 1:
        await status_msg.edit_text("❌ <b>Usage:</b> <code>/play &lt;YouTube_URL or Stream_URL&gt;</code>\nOr reply to an audio/video file.")
        return
    
    url = context.args[0]
    is_yt = "youtube.com" in url or "youtu.be" in url
        
    # Single URL
    if is_yt:
        await status_msg.edit_text("🎵 <i>Fetching video metadata...</i>", parse_mode='HTML')
        # We don't extract the direct stream url here to save time; we just get the title
        from yt_dlp import YoutubeDL
        def _get_title():
            with YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
                return ydl.extract_info(url, download=False).get('title', 'YouTube Audio')
        try:
            title = await asyncio.get_running_loop().run_in_executor(None, _get_title)
        except Exception:
            title = "YouTube Audio"
    else:
        title = "Direct Stream"

    queue_len = queue_manager.add(chat_id, {
        'url': url,
        'title': title,
        'video': False,
        'requester': update.effective_user.first_name
    })
    
    if queue_len == 1:
        await _start_playing_current(chat_id, assistant, status_msg)
    else:
        await status_msg.edit_text(f"✅ <b>Added to queue:</b> <i>{title}</i> (Position: {queue_len})", parse_mode='HTML')

async def _start_playing_current(chat_id: int, assistant, status_msg):
    """Helper to start the current queue item"""
    item = queue_manager.get_current(chat_id)
    if not item:
        return
        
    await status_msg.edit_text(f"🎵 <b>Playing:</b> <i>{item['title']}</i>\nProcessing stream...", parse_mode='HTML')
    
    url = item['url']
    if "youtube.com" in url or "youtu.be" in url:
        _, audio_url, _ = await YouTubeDownloader.get_stream_url(url, 'audio')
        if not audio_url:
            await status_msg.edit_text("❌ Failed to extract audio stream from YouTube URL.", parse_mode='HTML')
            queue_manager.next(chat_id)
            return
        stream_url = audio_url
    else:
        stream_url = url
        
    success = await assistant.play_stream(chat_id, stream_url, video=item['video'])
    
    if success:
        queue_manager.set_status_message(chat_id, status_msg)
        await status_msg.edit_text(
            f"✅ <b>Streaming Audio:</b> <i>{item['title']}</i>\n"
            f"👤 <b>Requested by:</b> {item['requester']}",
            parse_mode='HTML',
            reply_markup=get_player_keyboard()
        )
    else:
        await status_msg.edit_text("❌ Assistant failed to join or play stream in voice chat.", parse_mode='HTML')
        queue_manager.next(chat_id)

async def start_inline_download_audio(message, url: str, quality: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by inline button selection to transcode and upload audio"""
    try:
        await message.edit_text(f"📥 <i>Downloading audio ({quality}) from YouTube... Please wait...</i>", parse_mode='HTML')
        file_path, title = await YouTubeDownloader.download_media(url, 'audio', TEMP_DIR, quality)
        
        if not file_path or not os.path.exists(file_path):
            await message.edit_text("❌ Failed to download audio from YouTube. Please verify the URL and try again.", parse_mode='HTML')
            return
            
        await message.edit_text("📤 <i>Uploading audio file to Telegram...</i>", parse_mode='HTML')
        
        with open(file_path, 'rb') as audio_file:
            await context.bot.send_audio(
                chat_id=message.chat_id,
                audio=audio_file,
                title=title,
                caption=f"🎵 <b>{title}</b>\n\nDownloaded by @{context.bot.username}",
                parse_mode='HTML'
            )
            
        await message.delete()
        
        # Clean up file
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to delete temp file {file_path}: {e}")
            
    except Exception as e:
        logger.error(f"Error in start_inline_download_audio: {e}")
        await message.edit_text(f"❌ An error occurred during download: <code>{str(e)}</code>", parse_mode='HTML')

async def download_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download audio from YouTube with inline quality picker - /download_audio <URL>"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_html(
            "❌ <b>Usage:</b> <code>/download_audio &lt;YouTube_URL&gt;</code>\n"
            "Example: <code>/download_audio https://www.youtube.com/watch?v=dQw4w9WgXcQ</code>"
        )
        return
        
    url = context.args[0]
    
    # Extract video ID for compact callback_data (max 64 bytes limit)
    import re
    video_id = None
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&\s]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([^?\s]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^?\s]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([^?\s]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([^?\s]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break
            
    if not video_id:
        # Fallback to immediate download for non-youtube links at default quality
        status_msg = await update.message.reply_html("📥 <i>Downloading audio from URL... Please wait...</i>")
        try:
            file_path, title = await YouTubeDownloader.download_media(url, 'audio', TEMP_DIR)
            if not file_path or not os.path.exists(file_path):
                await status_msg.edit_text("❌ Failed to download audio. Verify the link.")
                return
            await status_msg.edit_text("📤 <i>Uploading audio file...</i>")
            with open(file_path, 'rb') as f:
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f, title=title)
            await status_msg.delete()
            os.remove(file_path)
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")
        return
        
    # Send quality selection menu
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [
            InlineKeyboardButton("🎵 128 kbps", callback_data=f"dl_aud|{video_id}|128k"),
            InlineKeyboardButton("🎵 192 kbps", callback_data=f"dl_aud|{video_id}|192k")
        ],
        [
            InlineKeyboardButton("🎵 256 kbps", callback_data=f"dl_aud|{video_id}|256k"),
            InlineKeyboardButton("🎵 320 kbps", callback_data=f"dl_aud|{video_id}|320k")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        "🎵 <b>Select Audio Quality:</b>\n"
        "Choose your preferred MP3 bitrate for the download below:",
        reply_markup=reply_markup
    )

async def pause_playback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pause current playback - /pause"""
    assistant = context.bot_data.get('assistant')
    if not assistant or not assistant.is_running or not PYTGCALLS_AVAILABLE:
        await update.message.reply_html("❌ Streaming is not active or assistant is not configured.")
        return
        
    chat_id = update.effective_chat.id
    if await assistant.pause(chat_id):
        await update.message.reply_html("⏸️ <b>Playback paused</b>")
    else:
        await update.message.reply_html("❌ Could not pause the stream.")

async def resume_playback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Resume playback - /resume"""
    assistant = context.bot_data.get('assistant')
    if not assistant or not assistant.is_running or not PYTGCALLS_AVAILABLE:
        await update.message.reply_html("❌ Streaming is not active or assistant is not configured.")
        return
        
    chat_id = update.effective_chat.id
    if await assistant.resume(chat_id):
        await update.message.reply_html("▶️ <b>Playback resumed</b>")
    else:
        await update.message.reply_html("❌ Could not resume the stream.")

async def stop_playback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop playback - /stop"""
    assistant = context.bot_data.get('assistant')
    if not assistant or not assistant.is_running or not PYTGCALLS_AVAILABLE:
        await update.message.reply_html("❌ Streaming is not active or assistant is not configured.")
        return
        
    chat_id = update.effective_chat.id
    if await assistant.stop_stream(chat_id):
        context.chat_data['current_stream'] = None
        await update.message.reply_html("⏹️ <b>Playback stopped & assistant left group call</b>")
    else:
        await update.message.reply_html("❌ Could not stop the stream.")
