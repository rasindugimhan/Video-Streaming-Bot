import asyncio
import subprocess
from typing import Optional, Callable
from utils.logger import get_logger
from utils.ffmpeg_utils import FFmpegHandler
from config import BUFFER_SIZE, CHUNK_SIZE

logger = get_logger(__name__)

class StreamManager:
    """Manage active streams"""
    
    def __init__(self):
        self.active_streams = {}
        self.process_map = {}
    
    async def start_audio_stream(self, 
                                stream_id: str, 
                                url: str,
                                on_data: Callable) -> bool:
        """Start streaming audio"""
        try:
            logger.info(f"Starting audio stream: {stream_id} from {url}")
            
            cmd = FFmpegHandler.convert_to_pcm(url)
            if not cmd:
                return False
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=BUFFER_SIZE
            )
            
            self.process_map[stream_id] = process
            self.active_streams[stream_id] = {
                'type': 'audio',
                'url': url,
                'process': process,
                'paused': False
            }
            
            # Start reading in background
            asyncio.create_task(self._read_stream(stream_id, on_data))
            return True
            
        except Exception as e:
            logger.error(f"Error starting audio stream: {e}")
            return False
    
    async def start_video_stream(self, 
                                stream_id: str, 
                                url: str,
                                on_data: Callable) -> bool:
        """Start streaming video"""
        try:
            logger.info(f"Starting video stream: {stream_id} from {url}")
            
            cmd = FFmpegHandler.convert_to_rawvideo(url)
            if not cmd:
                return False
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=BUFFER_SIZE
            )
            
            self.process_map[stream_id] = process
            self.active_streams[stream_id] = {
                'type': 'video',
                'url': url,
                'process': process,
                'paused': False
            }
            
            # Start reading in background
            asyncio.create_task(self._read_stream(stream_id, on_data))
            return True
            
        except Exception as e:
            logger.error(f"Error starting video stream: {e}")
            return False
    
    async def _read_stream(self, stream_id: str, on_data: Callable):
        """Read stream data and send to callback"""
        try:
            process = self.process_map.get(stream_id)
            if not process:
                return
            
            while process.poll() is None:
                chunk = process.stdout.read(CHUNK_SIZE)
                if chunk:
                    if callable(on_data):
                        await on_data(stream_id, chunk)
                else:
                    await asyncio.sleep(0.01)
                    
        except Exception as e:
            logger.error(f"Error reading stream {stream_id}: {e}")
        finally:
            self.stop_stream(stream_id)
    
    def pause_stream(self, stream_id: str) -> bool:
        """Pause a stream"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id]['paused'] = True
            logger.info(f"Stream paused: {stream_id}")
            return True
        return False
    
    def resume_stream(self, stream_id: str) -> bool:
        """Resume a stream"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id]['paused'] = False
            logger.info(f"Stream resumed: {stream_id}")
            return True
        return False
    
    def stop_stream(self, stream_id: str) -> bool:
        """Stop a stream"""
        try:
            if stream_id in self.process_map:
                process = self.process_map[stream_id]
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                del self.process_map[stream_id]
            
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            
            logger.info(f"Stream stopped: {stream_id}")
            return True
        except Exception as e:
            logger.error(f"Error stopping stream {stream_id}: {e}")
            return False
    
    def get_stream_status(self, stream_id: str) -> Optional[dict]:
        """Get stream status"""
        return self.active_streams.get(stream_id)
    
    def list_active_streams(self) -> list:
        """List all active streams"""
        return list(self.active_streams.keys())
