from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.logger import get_logger

logger = get_logger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    keyboard = [
        [
            InlineKeyboardButton("🎵 Music Commands", callback_data="help_music"),
            InlineKeyboardButton("🎬 Video Commands", callback_data="help_video"),
        ],
        [
            InlineKeyboardButton("📊 Current Status", callback_data="check_status"),
            InlineKeyboardButton("❓ Help & Info", callback_data="help_main"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🎵 <b>Welcome to Ewings!</b> 🎬\n\n"
        "I can stream high-quality audio and video links directly into your group's voice chats.\n\n"
        "Use the buttons below to discover my commands and check status:"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_text = """
<b>Bot Features:</b>

✅ Play/Stream audio & video streams in video chats
✅ <b>Download YouTube Audio/Video directly to your chat</b>
✅ Pause/Resume/Stop playback
✅ View playback status
✅ Support for HTTP/HTTPS/YouTube streams
✅ FFmpeg-based conversion

<b>Core Commands:</b>
• <code>/download_audio [YouTube_URL]</code> - Download YouTube audio as MP3
• <code>/download_video [YouTube_URL]</code> - Download YouTube video as MP4
• <code>/play_music [URL]</code> - Stream audio to group voice chat
• <code>/play_video [URL]</code> - Stream video to group voice chat

<b>Supported Formats:</b>
- Audio: MP3, WAV, M4A, FLAC, AAC
- Video: MP4, MKV, AVI, WEBM, MOV

<b>Requirements:</b>
- Bot must be admin in group/channel
- FFmpeg must be installed on the server

<b>Issues?</b> Contact the administrator.
    """
    await update.message.reply_text(help_text, parse_mode='HTML')

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
    
    status_text = "📊 <b>Active Streams:</b>\n"
    for stream_id in active_streams:
        stream_info = manager.get_stream_status(stream_id)
        if stream_info:
            status = "⏸️ Paused" if stream_info.get('paused') else "▶️ Playing"
            stream_type = stream_info.get('type', 'unknown').upper()
            status_text += f"\n• <b>{stream_type}</b>: {status}"
    
    await update.message.reply_text(status_text, parse_mode='HTML')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("dl_aud|"):
        _, video_id, quality = data.split("|")
        url = f"https://www.youtube.com/watch?v={video_id}"
        from handlers.music import start_inline_download_audio
        await start_inline_download_audio(query.message, url, quality, context)
        return
        
    elif data.startswith("dl_vid|"):
        _, video_id, quality = data.split("|")
        url = f"https://www.youtube.com/watch?v={video_id}"
        from handlers.video import start_inline_download_video
        await start_inline_download_video(query.message, url, quality, context)
        return

    # Player callbacks
    elif data == "cb_pause":
        assistant = context.bot_data.get('assistant')
        if assistant and await assistant.pause(query.message.chat_id):
            await query.answer("Paused playback")
        else:
            await query.answer("Could not pause", show_alert=True)
        return
        
    elif data == "cb_resume":
        assistant = context.bot_data.get('assistant')
        if assistant and await assistant.resume(query.message.chat_id):
            await query.answer("Resumed playback")
        else:
            await query.answer("Could not resume", show_alert=True)
        return
        
    elif data == "cb_stop":
        assistant = context.bot_data.get('assistant')
        from utils.queue_manager import queue_manager
        if assistant and await assistant.stop_stream(query.message.chat_id):
            queue_manager.clear(query.message.chat_id)
            await query.answer("Stopped playback and cleared queue")
            try:
                await query.edit_message_text("⏹ <b>Playback stopped & queue cleared.</b>", parse_mode='HTML')
            except Exception:
                pass
        else:
            await query.answer("Could not stop", show_alert=True)
        return
        
    elif data == "cb_next":
        assistant = context.bot_data.get('assistant')
        if assistant:
            await query.answer("Skipping to next...")
            import asyncio
            asyncio.create_task(assistant._handle_stream_end(query.message.chat_id))
        else:
            await query.answer("Error skipping", show_alert=True)
        return
        
    elif data == "cb_prev":
        assistant = context.bot_data.get('assistant')
        from utils.queue_manager import queue_manager
        if assistant:
            idx = queue_manager.current_index.get(query.message.chat_id, 0)
            if idx > 0:
                queue_manager.current_index[query.message.chat_id] = idx - 2
                if queue_manager.current_index[query.message.chat_id] < -1:
                    queue_manager.current_index[query.message.chat_id] = -1
                await query.answer("Playing previous...")
                import asyncio
                asyncio.create_task(assistant._handle_stream_end(query.message.chat_id))
            else:
                await query.answer("No previous track in queue", show_alert=True)
        else:
            await query.answer("Error playing previous", show_alert=True)
        return
        
    elif data == "cb_refresh":
        assistant = context.bot_data.get('assistant')
        from utils.queue_manager import queue_manager
        if assistant and assistant.pytgcalls:
            try:
                time_obj = await assistant.pytgcalls.played_time(query.message.chat_id)
                if time_obj is not None:
                    item = queue_manager.get_current(query.message.chat_id)
                    if item:
                        played = int(time_obj)
                        mins, secs = divmod(played, 60)
                        queue_len = len(queue_manager.get_queue(query.message.chat_id))
                        idx = queue_manager.current_index.get(query.message.chat_id, 0) + 1
                        
                        from handlers.music import get_player_keyboard
                        await query.edit_message_text(
                            f"▶️ <b>Now Playing:</b> <i>{item['title']}</i>\n"
                            f"⏱ <b>Played:</b> {mins:02d}:{secs:02d}\n"
                            f"📋 <b>Queue:</b> Track {idx} of {queue_len}\n"
                            f"👤 <b>Requested by:</b> {item.get('requester', 'Unknown')}",
                            parse_mode='HTML',
                            reply_markup=get_player_keyboard()
                        )
                        await query.answer("Refreshed!")
                        return
            except Exception as e:
                logger.error(f"Error fetching played_time: {e}")
        await query.answer("Could not fetch progress", show_alert=True)
        return

    # Queue management callbacks
    elif data == "cb_queue":
        await _show_queue(query.message.chat_id, query)
        return
        
    elif data == "cb_q_close":
        await query.message.delete()
        return
        
    elif data == "cb_q_clear":
        from utils.queue_manager import queue_manager
        chat_id = query.message.chat_id
        q = queue_manager.get_queue(chat_id)
        current_idx = queue_manager.current_index.get(chat_id, 0)
        
        # Keep only the current item
        if q and current_idx < len(q):
            current_item = q[current_idx]
            queue_manager.queues[chat_id] = [current_item]
            queue_manager.current_index[chat_id] = 0
            await query.answer("Queue cleared!")
        else:
            queue_manager.clear(chat_id)
            await query.answer("Queue cleared!")
            
        await _show_queue(chat_id, query)
        return
        
    elif data.startswith("cb_q_del_"):
        from utils.queue_manager import queue_manager
        idx_to_remove = int(data.split("_")[-1])
        if queue_manager.remove_item(query.message.chat_id, idx_to_remove):
            await query.answer("Track removed")
        else:
            await query.answer("Could not remove track", show_alert=True)
        await _show_queue(query.message.chat_id, query)
        return
    
    if data == "help_music":
        text = (
            "🎵 <b>Music & Download Commands:</b>\n\n"
            "• <code>/download_audio [URL]</code> - Download audio from YouTube as MP3\n"
            "• <code>/play [URL]</code> - Stream music in video chat\n"
            "• <code>/pause</code> - Pause current playback\n"
            "• <code>/resume</code> - Resume playback\n"
            "• <code>/stop</code> - Stop playback\n"
            "• <code>/queue</code> - View and manage the queue\n\n"
            "<i>Example:</i> <code>/download_audio https://www.youtube.com/watch?v=dQw4w9WgXcQ</code>"
        )
    elif data == "help_video":
        text = (
            "🎬 <b>Video & Download Commands:</b>\n\n"
            "• <code>/download_video [URL]</code> - Download video from YouTube as MP4\n"
            "• <code>/vplay [URL]</code> - Stream video in video chat\n"
            "• <code>/play_stream [URL]</code> - Stream with auto-detect type\n"
            "• <code>/queue</code> - View and manage the queue\n\n"
            "<i>Example:</i> <code>/download_video https://www.youtube.com/watch?v=dQw4w9WgXcQ</code>"
        )
    elif data == "check_status":
        manager = context.bot_data.get('stream_manager')
        if not manager:
            text = "❌ Stream manager not initialized"
        else:
            active_streams = manager.list_active_streams()
            if not active_streams:
                text = "❌ <b>No active streams</b>"
            else:
                text = "📊 <b>Active Streams:</b>\n"
                for stream_id in active_streams:
                    stream_info = manager.get_stream_status(stream_id)
                    if stream_info:
                        status = "⏸️ Paused" if stream_info.get('paused') else "▶️ Playing"
                        stream_type = stream_info.get('type', 'unknown').upper()
                        text += f"\n• <b>{stream_type}</b>: {status}"
    elif data == "help_main":
        text = (
            "ℹ️ <b>Ewings Bot Info:</b>\n\n"
            "✅ Streams audio and video using FFmpeg\n"
            "✅ Supports MP3, WAV, MP4, MKV, and HTTP/RTMP streams\n"
            "⚠️ Bot must be an Administrator in the group/channel\n"
        )
    elif data == "back_to_menu":
        keyboard = [
            [
                InlineKeyboardButton("🎵 Music Commands", callback_data="help_music"),
                InlineKeyboardButton("🎬 Video Commands", callback_data="help_video"),
            ],
            [
                InlineKeyboardButton("📊 Current Status", callback_data="check_status"),
                InlineKeyboardButton("❓ Help & Info", callback_data="help_main"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_text = (
            "🎵 <b>Welcome to Ewings!</b> 🎬\n\n"
            "I can stream high-quality audio and video links directly into your group's voice chats.\n\n"
            "Use the buttons below to discover my commands and check status:"
        )
        await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')
        return
    else:
        text = "Unknown option"
        
    keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def _show_queue(chat_id: int, query_or_update):
    """Helper to render the queue UI"""
    from utils.queue_manager import queue_manager
    q = queue_manager.get_queue(chat_id)
    current_idx = queue_manager.current_index.get(chat_id, 0)
    
    if not q:
        text = "📭 <b>The queue is currently empty.</b>"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Close", callback_data="cb_q_close")]])
    else:
        text = "📋 <b>Current Queue:</b>\n\n"
        keyboard = []
        
        # Display up to 10 upcoming tracks
        start_idx = current_idx
        end_idx = min(start_idx + 10, len(q))
        
        for i in range(start_idx, end_idx):
            item = q[i]
            prefix = "▶️" if i == current_idx else f"{i - current_idx}."
            text += f"{prefix} <i>{item['title']}</i>\n"
            
            # Add a remove button for upcoming tracks (not the currently playing one)
            if i > current_idx:
                keyboard.append([InlineKeyboardButton(f"🗑 Remove Track {i - current_idx}", callback_data=f"cb_q_del_{i}")])
                
        if len(q) > end_idx:
            text += f"\n<i>... and {len(q) - end_idx} more tracks.</i>"
            
        # Add bottom controls
        keyboard.append([
            InlineKeyboardButton("🗑 Clear All Upcoming", callback_data="cb_q_clear"),
            InlineKeyboardButton("❌ Close", callback_data="cb_q_close")
        ])
        markup = InlineKeyboardMarkup(keyboard)
        
    if hasattr(query_or_update, 'message') and query_or_update.message:
        # It's a callback query
        await query_or_update.message.reply_html(text, reply_markup=markup)
        try:
            await query_or_update.answer()
        except:
            pass
    else:
        # It's a command update
        await query_or_update.message.reply_html(text, reply_markup=markup)

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /queue command"""
    await _show_queue(update.effective_chat.id, update)
