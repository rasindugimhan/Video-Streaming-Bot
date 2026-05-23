import asyncio
from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class QueueManager:
    """Manages playback queues for different chats"""
    
    def __init__(self):
        self.queues: Dict[int, List[Dict[str, Any]]] = {}
        self.current_index: Dict[int, int] = {}
        # To store message IDs of the "Now Playing" messages so we can update them
        self.status_messages: Dict[int, Any] = {}

    def add(self, chat_id: int, item: Dict[str, Any]) -> int:
        """Add an item to the end of the queue. Returns the queue length."""
        if chat_id not in self.queues:
            self.queues[chat_id] = []
            self.current_index[chat_id] = 0
            
        self.queues[chat_id].append(item)
        return len(self.queues[chat_id])

    def add_multiple(self, chat_id: int, items: List[Dict[str, Any]]) -> int:
        """Add multiple items (e.g. from playlist) to the queue"""
        if chat_id not in self.queues:
            self.queues[chat_id] = []
            self.current_index[chat_id] = 0
            
        self.queues[chat_id].extend(items)
        return len(self.queues[chat_id])

    def get_current(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get the currently playing item"""
        idx = self.current_index.get(chat_id, 0)
        q = self.queues.get(chat_id, [])
        if idx < len(q):
            return q[idx]
        return None

    def get_queue(self, chat_id: int) -> List[Dict[str, Any]]:
        """Get the full queue for a chat"""
        return self.queues.get(chat_id, [])

    def next(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Advance the queue to the next item and return it"""
        idx = self.current_index.get(chat_id, 0)
        q = self.queues.get(chat_id, [])
        if idx + 1 < len(q):
            self.current_index[chat_id] = idx + 1
            return self.get_current(chat_id)
        return None

    def prev(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Go back to the previous item in the queue"""
        idx = self.current_index.get(chat_id, 0)
        if idx > 0:
            self.current_index[chat_id] = idx - 1
            return self.get_current(chat_id)
        return None

    def clear(self, chat_id: int):
        """Clear the queue and indices for a chat"""
        self.queues.pop(chat_id, None)
        self.current_index.pop(chat_id, None)
        self.status_messages.pop(chat_id, None)

    def is_empty(self, chat_id: int) -> bool:
        """Check if queue is empty"""
        return len(self.queues.get(chat_id, [])) == 0

    def set_status_message(self, chat_id: int, message):
        """Store the Telegram message object to edit it later"""
        self.status_messages[chat_id] = message
        
    def get_status_message(self, chat_id: int):
        """Get the stored Telegram message object"""
        return self.status_messages.get(chat_id)

# Global queue manager instance
queue_manager = QueueManager()
