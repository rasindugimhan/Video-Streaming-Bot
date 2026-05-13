"""
Main Telegram Bot - Music & Video Streaming
"""

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    filters
)
from telegram import Update
from utils.logger import get_logger
from utils.ffmpeg_utils import FFmpegHandler
from utils.streaming import StreamManager
from handlers.commands import (
    start_command,
    help_command,
    status_command,
    error_handler
)
from handlers.music import (
    play_music,
    pause_playback,
    resume_playback,
    stop_playback
)
from handlers.video import (
    play_video,
    play_stream
)
from config import BOT_TOKEN

logger = get_logger(__name__)

class TelegramMusicBot:
    """Main Telegram Music Bot class"""
    
    def __init__(self, token: str):
        self.token = token
        self.app = None
        self.stream_manager = StreamManager()
    
    async def post_init(self, app: Application) -> None:
        """Post-initialization setup"""
        logger.info("Bot post-init setup started")
        
        # Check FFmpeg installation
        if not FFmpegHandler.check_ffmpeg_installed():
            logger.warning("FFmpeg not installed - streaming may not work")
        
        # Initialize stream manager in bot data
        app.bot_data['stream_manager'] = self.stream_manager
        
        logger.info("Bot post-init setup completed")
    
    def setup_handlers(self) -> None:
        """Setup command handlers"""
        
        # Command handlers
        self.app.add_handler(CommandHandler("start", start_command))
        self.app.add_handler(CommandHandler("help", help_command))
        self.app.add_handler(CommandHandler("status", status_command))
        
        # Music handlers
        self.app.add_handler(CommandHandler("play_music", play_music))
        self.app.add_handler(CommandHandler("pause", pause_playback))
        self.app.add_handler(CommandHandler("resume", resume_playback))
        self.app.add_handler(CommandHandler("stop", stop_playback))
        
        # Video handlers
        self.app.add_handler(CommandHandler("play_video", play_video))
        self.app.add_handler(CommandHandler("play_stream", play_stream))
        
        # Error handler
        self.app.add_error_handler(error_handler)
        
        logger.info("Command handlers setup completed")
    
    async def initialize(self) -> None:
        """Initialize the bot"""
        try:
            self.app = Application.builder().token(self.token).build()
            
            # Setup post-init
            self.app.post_init = self.post_init
            
            # Setup handlers
            self.setup_handlers()
            
            logger.info("Bot initialization completed")
            
        except Exception as e:
            logger.error(f"Error initializing bot: {e}")
            raise
    
    async def start(self) -> None:
        """Start the bot"""
        try:
            logger.info("Starting bot...")
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("Bot started successfully")
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the bot"""
        try:
            logger.info("Stopping bot...")
            
            # Stop all active streams
            for stream_id in self.stream_manager.list_active_streams():
                self.stream_manager.stop_stream(stream_id)
            
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

def main():
    """Main entry point"""
    import asyncio
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment variables")
        raise ValueError("BOT_TOKEN environment variable is required")
    
    bot = TelegramMusicBot(BOT_TOKEN)
    
    try:
        asyncio.run(bot.initialize())
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        asyncio.run(bot.stop())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
