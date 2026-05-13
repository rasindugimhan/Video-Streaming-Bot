#!/usr/bin/env python3
"""
Telegram Music & Video Streaming Bot
Main entry point
"""

import sys
import asyncio
from bot import TelegramMusicBot
from config import BOT_TOKEN
from utils.logger import get_logger

logger = get_logger(__name__)

async def main():
    """Main function"""
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in .env file")
        sys.exit(1)
    
    logger.info("Initializing Telegram Music Bot...")
    
    bot = TelegramMusicBot(BOT_TOKEN)
    
    try:
        await bot.initialize()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
