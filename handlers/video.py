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
from handlers.music import get_player_keyboard

async def play_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Play video in video chat - /vplay <URL> or reply to file"""
    
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
    if replied and (replied.video or replied.document):
        await status_msg.edit_text("📥 <i>Downloading video file to server...</i>", parse_mode='HTML')
        file_obj = replied.video or replied.document
        
        file_ext = ".mp4"
        if getattr(replied.document, 'file_name', None):
            _, file_ext = os.path.splitext(replied.document.file_name)
            
        file_path = os.path.join(TEMP_DIR, f"dl_{file_obj.file_id}{file_ext}")
        
        if not os.path.exists(file_path):
            new_file = await context.bot.get_file(file_obj.file_id)
            await new_file.download_to_drive(file_path)
            
        title = getattr(file_obj, 'title', getattr(file_obj, 'file_name', 'Local Video'))
        
        queue_len = queue_manager.add(chat_id, {
            'url': file_path,
            'title': title,
            'video': True,
            'requester': update.effective_user.first_name
        })
        
        if queue_len == 1:
            await _start_playing_current_video(chat_id, assistant, status_msg)
        else:
            await status_msg.edit_text(f"✅ <b>Added to queue:</b> <i>{title}</i> (Position: {queue_len})", parse_mode='HTML')
        return

    if not context.args or len(context.args) < 1:
        await status_msg.edit_text("❌ <b>Usage:</b> <code>/vplay &lt;YouTube_URL or Stream_URL&gt;</code>\nOr reply to a video file.")
        return
    
    url = context.args[0]
    is_yt = "youtube.com" in url or "youtu.be" in url
        
    # Single URL
    if is_yt:
        await status_msg.edit_text("🎬 <i>Fetching video metadata...</i>", parse_mode='HTML')
        from yt_dlp import YoutubeDL
        def _get_title():
            with YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
                return ydl.extract_info(url, download=False).get('title', 'YouTube Video')
        try:
            title = await asyncio.get_running_loop().run_in_executor(None, _get_title)
        except Exception:
            title = "YouTube Video"
    else:
        title = "Direct Video Stream"

    queue_len = queue_manager.add(chat_id, {
        'url': url,
        'title': title,
        'video': True,
        'requester': update.effective_user.first_name
    })
    
    if queue_len == 1:
        await _start_playing_current_video(chat_id, assistant, status_msg)
    else:
        await status_msg.edit_text(f"✅ <b>Added to queue:</b> <i>{title}</i> (Position: {queue_len})", parse_mode='HTML')

async def _start_playing_current_video(chat_id: int, assistant, status_msg):
    """Helper to start the current video queue item"""
    item = queue_manager.get_current(chat_id)
    if not item:
        return
        
    await status_msg.edit_text(f"🎬 <b>Playing:</b> <i>{item['title']}</i>\nProcessing video stream...", parse_mode='HTML')
    
    url = item['url']
    audio_url = None
    if "youtube.com" in url or "youtu.be" in url:
        video_url, audio_url, _ = await YouTubeDownloader.get_stream_url(url, 'video')
        if not video_url:
            await status_msg.edit_text("❌ Failed to extract video stream from YouTube URL.", parse_mode='HTML')
            queue_manager.next(chat_id)
            return
        stream_url = video_url
    else:
        stream_url = url
        
    success = await assistant.play_stream(chat_id, stream_url, audio_url=audio_url, video=item['video'])
    
    if success:
        queue_manager.set_status_message(chat_id, status_msg)
        await status_msg.edit_text(
            f"✅ <b>Streaming Video:</b> <i>{item['title']}</i>\n"
            f"👤 <b>Requested by:</b> {item['requester']}",
            parse_mode='HTML',
            reply_markup=get_player_keyboard()
        )
    else:
        await status_msg.edit_text("❌ Assistant failed to join or play video stream in voice chat.", parse_mode='HTML')
        queue_manager.next(chat_id)

async def start_inline_download_video(message, url: str, quality: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by inline button selection to download and upload video"""
    try:
        await message.edit_text(f"📥 <i>Downloading video ({quality}) from YouTube... Please wait...</i>", parse_mode='HTML')
        file_path, title = await YouTubeDownloader.download_media(url, 'video', TEMP_DIR, quality)
        
        if not file_path or not os.path.exists(file_path):
            await message.edit_text("❌ Failed to download video from YouTube. Please verify the URL and try again.", parse_mode='HTML')
            return
            
        await message.edit_text("📤 <i>Uploading video file to Telegram...</i>", parse_mode='HTML')
        
        with open(file_path, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=message.chat_id,
                video=video_file,
                caption=f"🎬 <b>{title}</b>\n\nDownloaded by @{context.bot.username}",
                parse_mode='HTML'
            )
            
        await message.delete()
        
        # Clean up file
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to delete temp file {file_path}: {e}")
            
    except Exception as e:
        logger.error(f"Error in start_inline_download_video: {e}")
        await message.edit_text(f"❌ An error occurred during download: <code>{str(e)}</code>", parse_mode='HTML')

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download video from YouTube with inline quality picker - /download_video <URL>"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_html(
            "❌ <b>Usage:</b> <code>/download_video &lt;YouTube_URL&gt;</code>\n"
            "Example: <code>/download_video https://www.youtube.com/watch?v=dQw4w9WgXcQ</code>"
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
        # Fallback to immediate download for non-youtube links at best quality
        status_msg = await update.message.reply_html("📥 <i>Downloading video from URL... Please wait...</i>")
        try:
            file_path, title = await YouTubeDownloader.download_media(url, 'video', TEMP_DIR)
            if not file_path or not os.path.exists(file_path):
                await status_msg.edit_text("❌ Failed to download video. Verify the link.")
                return
            await status_msg.edit_text("📤 <i>Uploading video file...</i>")
            with open(file_path, 'rb') as f:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption=f"🎬 <b>{title}</b>")
            await status_msg.delete()
            os.remove(file_path)
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")
        return
        
    # Send quality selection menu
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [
            InlineKeyboardButton("🎬 360p", callback_data=f"dl_vid|{video_id}|360p"),
            InlineKeyboardButton("🎬 480p", callback_data=f"dl_vid|{video_id}|480p")
        ],
        [
            InlineKeyboardButton("🎬 720p", callback_data=f"dl_vid|{video_id}|720p"),
            InlineKeyboardButton("🎬 1080p", callback_data=f"dl_vid|{video_id}|1080p")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        "🎬 <b>Select Video Quality:</b>\n"
        "Choose your preferred MP4 resolution for the download below:",
        reply_markup=reply_markup
    )

async def play_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Auto-detect and stream content"""
    # For simplicity, route to play_video
    await play_video(update, context)
