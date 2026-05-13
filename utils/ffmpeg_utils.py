import subprocess
import os
from utils.logger import get_logger

logger = get_logger(__name__)

class FFmpegHandler:
    """Handle FFmpeg operations for streaming"""
    
    @staticmethod
    def check_ffmpeg_installed():
        """Check if FFmpeg is installed"""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, 
                         check=True)
            logger.info("FFmpeg is installed")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("FFmpeg is not installed or not in PATH")
            return False
    
    @staticmethod
    def get_stream_info(url):
        """Get information about a stream"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1:noprint_wrappers=1',
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                try:
                    duration = float(result.stdout.strip())
                    logger.debug(f"Stream duration: {duration} seconds")
                    return {'duration': duration}
                except ValueError:
                    return None
            return None
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return None
    
    @staticmethod
    def convert_to_pcm(input_url, output_path='-', bit_rate='192k'):
        """Convert audio stream to PCM format for Telegram"""
        try:
            cmd = [
                'ffmpeg',
                '-i', input_url,
                '-acodec', 'pcm_s16le',
                '-ar', '48000',
                '-ac', '2',
                '-b:a', bit_rate,
                '-f', 's16le',
                output_path
            ]
            logger.info(f"Converting stream with command: {' '.join(cmd)}")
            return cmd
        except Exception as e:
            logger.error(f"Error creating conversion command: {e}")
            return None
    
    @staticmethod
    def convert_to_rawvideo(input_url, output_path='-', resolution='1280x720', fps=30):
        """Convert video stream to raw video format for Telegram"""
        try:
            cmd = [
                'ffmpeg',
                '-i', input_url,
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'yuv420p',
                '-s', resolution,
                '-r', str(fps),
                '-f', 'rawvideo',
                output_path
            ]
            logger.info(f"Converting video stream with command: {' '.join(cmd)}")
            return cmd
        except Exception as e:
            logger.error(f"Error creating video conversion command: {e}")
            return None
