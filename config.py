import os
import sys
from dotenv import load_dotenv
import logging

def setup_wizard():
    """Interactive wizard to get configuration inputs if missing"""
    env_path = '.env'
    config_values = {}
    
    # Read existing .env if it exists
    existing_lines = []
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        except Exception:
            pass
            
    # Parse existing values to check if they are set
    for line in existing_lines:
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            parts = line.split('=', 1)
            if len(parts) == 2:
                config_values[parts[0].strip()] = parts[1].strip()
            
    # Define what we need
    essential_keys = {
        'BOT_TOKEN': {
            'prompt': '🤖 Enter your Telegram Bot Token (from @BotFather): ',
            'placeholder': '',
            'required': True
        },
        'ADMIN_USER_ID': {
            'prompt': '👑 Enter Admin Telegram User ID (optional, press Enter to skip): ',
            'placeholder': '0',
            'required': False
        },
        'API_ID': {
            'prompt': '🔑 Enter Telegram API ID (from my.telegram.org, optional, press Enter to skip): ',
            'placeholder': 'your_api_id_here',
            'required': False
        },
        'API_HASH': {
            'prompt': '🔒 Enter Telegram API HASH (from my.telegram.org, optional, press Enter to skip): ',
            'placeholder': 'your_api_hash_here',
            'required': False
        }
    }
    
    needs_setup = False
    for key, info in essential_keys.items():
        val = config_values.get(key, '')
        if not val or val == info['placeholder']:
            needs_setup = True
            break
            
    if not needs_setup:
        return
        
    # Check if standard input is a TTY
    if not sys.stdin.isatty():
        return
        
    print("=" * 60)
    print("🌟 EWINGS BOT - INITIAL SETUP WIZARD 🌟")
    print("Some essential configuration inputs are missing in your .env file.")
    print("Please provide them below to set up your bot instantly.")
    print("=" * 60)
    
    updated_values = {}
    try:
        for key, info in essential_keys.items():
            current_val = config_values.get(key, '')
            
            # If already set to a non-placeholder value, keep it
            if current_val and current_val != info['placeholder']:
                updated_values[key] = current_val
                continue
                
            while True:
                user_input = input(info['prompt']).strip()
                if not user_input:
                    if info['required']:
                        print("❌ This input is required. Please enter a valid value.")
                        continue
                    else:
                        user_input = info['placeholder']
                updated_values[key] = user_input
                break
    except (EOFError, KeyboardInterrupt):
        print("\n⚠️ Setup wizard interrupted. Using defaults/placeholders.")
        return
            
    # Now merge and update .env
    new_lines = []
    keys_written = set()
    
    for line in existing_lines:
        stripped = line.strip()
        if stripped and '=' in stripped and not stripped.startswith('#'):
            parts = stripped.split('=', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                if key in updated_values:
                    new_lines.append(f"{key}={updated_values[key]}\n")
                    keys_written.add(key)
                    continue
        new_lines.append(line)
        
    # Append any remaining keys
    for key, val in updated_values.items():
        if key not in keys_written:
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines[-1] += '\n'
            new_lines.append(f"{key}={val}\n")
            
    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("=" * 60)
        print("✅ Configuration successfully saved to .env!")
        print("=" * 60)
        print()
    except Exception as e:
        print(f"❌ Failed to save configuration to .env: {e}")

# Run setup wizard before loading env
setup_wizard()

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')

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
