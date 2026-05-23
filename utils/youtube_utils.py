import yt_dlp
import os
import asyncio
from utils.logger import get_logger

logger = get_logger(__name__)

_YT_BYPASS_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
    # Use the Android player client — avoids the "sign in to confirm" bot detection
    # that YouTube applies to datacenter IPs when using the default web client
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android'],
            'skip': ['dash', 'hls'],
        }
    },
    # Retry on transient errors
    'retries': 1,
    'fragment_retries': 1,
    'ignoreerrors': False,
}

def get_youtube_cookies_path() -> str | None:
    """
    Check for YouTube cookies in environment variables or a local file.
    Returns the path to the cookies file, or None.
    """
    # 1. Check for cookies content in environment variable
    yt_cookies_env = os.getenv('YT_COOKIES')
    if yt_cookies_env:
        try:
            os.makedirs('temp', exist_ok=True)
            cookie_path = os.path.join('temp', 'youtube_cookies.txt')
            with open(cookie_path, 'w', encoding='utf-8') as f:
                f.write(yt_cookies_env.strip())
            logger.info(f"Loaded YouTube cookies from YT_COOKIES environment variable into {cookie_path}")
            return cookie_path
        except Exception as e:
            logger.error(f"Error saving YT_COOKIES to file: {e}")
            
    # 2. Check for local cookies.txt file
    local_cookies = 'cookies.txt'
    if os.path.exists(local_cookies):
        logger.info(f"Using local {local_cookies} file")
        return local_cookies
        
    return None

class YouTubeDownloader:
    """Helper class to handle YouTube streaming and downloading using yt-dlp"""
    
    @staticmethod
    async def get_stream_url(url: str, stream_type: str = 'audio') -> tuple[str | None, str | None, str | None]:
        """
        Extract direct streaming URL from a YouTube video.
        Returns (video_url, audio_url, title). For audio-only, video_url is None.
        """
        logger.info(f"Starting get_stream_url extraction for: {url} (Type: {stream_type})")
        try:
            loop = asyncio.get_running_loop()
            
            def _extract():
                cookies_path = get_youtube_cookies_path()
                ydl_opts = {
                    **_YT_BYPASS_OPTS,
                    'format': 'bestaudio/best' if stream_type == 'audio' else 'bestvideo+bestaudio/best',
                }
                if cookies_path:
                    logger.info("Using YouTube cookies for extraction.")
                    ydl_opts['cookiefile'] = cookies_path
                    ydl_opts['extractor_args'] = {
                        'youtube': {
                            'player_client': ['ios', 'android'],
                        }
                    }
                else:
                    logger.info("No YouTube cookies found. Using default clients.")
                    ydl_opts['extractor_args'] = {
                        'youtube': {
                            'player_client': ['ios', 'android'],
                        }
                    }
                    
                logger.info(f"Extracting info using yt-dlp. Options: format={ydl_opts['format']}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Unknown Title')
                    logger.info(f"Successfully fetched info for: {title}")
                    
                    if stream_type == 'audio':
                        # Retrieve the best direct URL for audio
                        if 'requested_formats' in info:
                            logger.info("Found requested_formats in yt-dlp info.")
                            for f in info['requested_formats']:
                                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                                    logger.info(f"Found audio-only format: {f.get('format_id')}")
                                    return None, f['url'], title
                        
                        if 'formats' in info:
                            logger.info("Searching through all formats for an audio-only stream.")
                            audio_formats = [f for f in info['formats'] if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                            if audio_formats:
                                logger.info(f"Found audio stream from formats: {audio_formats[-1].get('format_id')}")
                                return None, audio_formats[-1]['url'], title
                                
                        logger.warning("No discrete audio-only format found. Falling back to default URL.")
                        return None, info.get('url'), title
                    else:
                        # Video type
                        video_url = None
                        audio_url = None
                        
                        if 'requested_formats' in info:
                            logger.info("Found requested_formats for video/audio.")
                            for f in info['requested_formats']:
                                if f.get('vcodec') != 'none':
                                    logger.info(f"Selected video format: {f.get('format_id')}")
                                    video_url = f['url']
                                elif f.get('acodec') != 'none':
                                    logger.info(f"Selected audio format: {f.get('format_id')}")
                                    audio_url = f['url']
                            if video_url and audio_url:
                                logger.info("Successfully extracted both video and audio discrete URLs.")
                                return video_url, audio_url, title
                                
                        if 'formats' in info:
                            logger.info("Searching through all formats for a combined video+audio stream.")
                            # Try to find a combined format
                            combined = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                            if combined:
                                logger.info(f"Found combined stream format: {combined[-1].get('format_id')}")
                                return combined[-1]['url'], combined[-1]['url'], title
                                
                        logger.warning("No standard format match. Falling back to default URL for both.")
                        return info.get('url'), info.get('url'), title
            
            return await loop.run_in_executor(None, _extract)
        except Exception as e:
            logger.error(f"Error extracting stream URL from YouTube: {e}", exc_info=True)
            return None, None, None

    @staticmethod
    async def extract_playlist(url: str) -> list[dict]:
        """
        Extract entries from a YouTube playlist.
        Returns a list of dicts: [{'title': str, 'url': str}, ...]
        """
        logger.info(f"Extracting playlist: {url}")
        try:
            loop = asyncio.get_running_loop()
            
            def _extract():
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True,  # Extremely fast, only gets metadata, not full streams
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['ios', 'android'],
                        }
                    }
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    entries = []
                    if 'entries' in info:
                        for entry in info['entries']:
                            if entry and entry.get('url'):
                                # yt-dlp might return relative URLs or video IDs for entries
                                entry_url = entry.get('url')
                                if not entry_url.startswith('http'):
                                    entry_url = f"https://www.youtube.com/watch?v={entry.get('id', entry_url)}"
                                    
                                entries.append({
                                    'title': entry.get('title', 'Unknown Title'),
                                    'url': entry_url
                                })
                    elif 'url' in info:
                        # Single video fallback
                        entries.append({
                            'title': info.get('title', 'Unknown Title'),
                            'url': info.get('url') if info.get('url').startswith('http') else url
                        })
                    
                    return entries
            
            return await loop.run_in_executor(None, _extract)
        except Exception as e:
            logger.error(f"Error extracting playlist: {e}", exc_info=True)
            return []
            
    @staticmethod
    async def download_media(url: str, download_type: str = 'audio', output_dir: str = 'temp', quality: str = None) -> tuple[str | None, str | None]:
        """
        Download media from YouTube with quality option.
        Returns (file_path, title) or (None, None).
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            if download_type == 'audio':
                # Parse audio quality (e.g. 192k -> 192, 320 -> 320)
                audio_kbps = '192'
                if quality:
                    clean_quality = str(quality).lower().replace('k', '').strip()
                    if clean_quality in ['128', '192', '256', '320']:
                        audio_kbps = clean_quality
                        
                ydl_opts = {
                    **_YT_BYPASS_OPTS,
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': audio_kbps,
                    }],
                }
            else:
                # Parse video quality (e.g. 720p -> 720, 1080 -> 1080)
                video_format = 'bestvideo+bestaudio/best'
                if quality:
                    clean_res = str(quality).lower().replace('p', '').strip()
                    if clean_res in ['144', '240', '360', '480', '720', '1080', '1440', '2160']:
                        video_format = f"bestvideo[height<={clean_res}]+bestaudio/best[height<={clean_res}]/best"
                        
                ydl_opts = {
                    **_YT_BYPASS_OPTS,
                    'format': video_format,
                    'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
                    # Merge video+audio into mp4 container
                    'merge_output_format': 'mp4',
                }
                
            cookies_path = get_youtube_cookies_path()
            if cookies_path:
                ydl_opts['cookiefile'] = cookies_path
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        'player_client': ['ios', 'android'],
                        'skip': ['dash', 'hls'],
                    }
                }
                
            loop = asyncio.get_event_loop()
            
            def _download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    title = info.get('title', 'Unknown Title')
                    
                    if download_type == 'audio':
                        base, _ = os.path.splitext(filename)
                        filename = f"{base}.mp3"
                    elif download_type == 'video':
                        # yt-dlp may change extension after merge
                        base, _ = os.path.splitext(filename)
                        for ext in ['.mp4', '.mkv', '.webm']:
                            candidate = f"{base}{ext}"
                            if os.path.exists(candidate):
                                filename = candidate
                                break
                        
                    return filename, title
                    
            return await loop.run_in_executor(None, _download)
            
        except Exception as e:
            logger.error(f"Error downloading media from YouTube: {e}")
            return None, None
