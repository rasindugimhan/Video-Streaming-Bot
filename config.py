import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Streaming Configuration
MAX_STREAM_DURATION = int(os.getenv('MAX_STREAM_DURATION', 3600))
BUFFER_SIZE = int(os.getenv('BUFFER_SIZE', 1024000))
CHUNK_SIZE = 4096

# Directories
LOG_DIR = 'logs'
TEMP_DIR = 'temp'
STREAMS_DIR = 'streams'

# Create required directories
for directory in [LOG_DIR, TEMP_DIR, STREAMS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Supported formats
SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a', '.flac', '.aac']
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mkv', '.avi', '.webm', '.mov']
SUPPORTED_STREAM_PROTOCOLS = ['http://', 'https://', 'rtmp://']
