# 🎵 Ewings Telegram Media Bot 🎬

Ewings is a powerful and advanced Telegram bot designed to stream high-quality audio and video directly into your group's voice chats. Built using Python, Pyrogram, and PyTgCalls, it supports advanced queueing, interactive inline controls, YouTube playlists, and native Telegram media streaming!

## ✨ Features

- **High-Quality Streaming:** Stream music and videos natively into Telegram voice chats.
- **Advanced Queueing:** Add multiple songs/videos, and let the bot auto-play the next item when one finishes.
- **Playlist Support:** Paste a YouTube playlist URL, and the bot will instantly load all tracks into the queue.
- **Telegram Native Media:** Reply to any audio or video file directly in Telegram with `/play` or `/vplay` to stream it.
- **Interactive UI:** Control playback with dynamic inline keyboards (Pause, Resume, Next, Prev, Stop, Refresh).
- **Direct Link Support:** Stream `m3u8` and RTMP links natively.
- **Media Download:** Users can download YouTube media directly to their device via `/download_audio` and `/download_video`.

## 🛠 Prerequisites

- Python 3.10+
- FFmpeg (Installed on the system and added to PATH)
- Telegram API ID & API Hash (from [my.telegram.org](https://my.telegram.org))
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

## ⚙️ Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/Ewings.git
   cd Ewings
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *Note: Due to binary incompatibilities with newer python versions on some hosts, the bot includes a custom script to securely download and extract `pytgcalls` natively on boot (e.g., in Railway environments).*

3. **Environment Configuration:**
   Create a `.env` file in the root directory and add your credentials:
   ```env
   BOT_TOKEN=your_bot_token_here
   API_ID=your_api_id_here
   API_HASH=your_api_hash_here
   SESSION_STRING=your_pyrogram_session_string_here  # Optional: For the userbot
   ```

4. **Run the bot:**
   ```bash
   python main.py
   ```

## 🚀 Commands

- `/start` - Start the bot and see the welcome message.
- `/help` - View detailed help information.
- `/play <url>` - Stream music to voice chat.
- `/vplay <url>` - Stream video to voice chat.
- `/pause` - Pause playback.
- `/resume` - Resume playback.
- `/stop` - Stop playback and clear the queue.
- `/download_audio <url>` - Download YouTube audio.
- `/download_video <url>` - Download YouTube video.

## 🚢 Deployment on Railway

This bot is optimized for deployment on [Railway.app](https://railway.app/).
1. Connect your GitHub repository to a new Railway project.
2. Add the required environment variables in the Railway Dashboard.
3. The included `nixpacks.toml` automatically installs FFmpeg and sets up the environment!

## 📜 License
This project is open-source. Feel free to use and modify!

---

## 📞 Support & Contact
If you have any issues, questions, or suggestions, feel free to contact me:
- **GitHub**: [rasindugimhan](https://github.com/rasindugimhan)
- **Telegram**: [@Dexter_RG](https://t.me/Dexter_RG)
