import json
import os
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ConversationMemory:
    def __init__(self, memory_file: str = 'conversation_memory.json'):
        self.memory_file = memory_file
        self.conversations = self._load_conversations()
    
    def _load_conversations(self) -> Dict[str, List[Dict]]:
        """Load conversation history from file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading conversation memory: {e}")
            return {}
    
    def _save_conversations(self):
        """Save conversation history to file"""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.conversations, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving conversation memory: {e}")
    
    def add_message(self, sender_email: str, message_type: str, content: str, 
                   subject: str = "", message_id: str = ""):
        """
        Add a message to the conversation memory
        
        Args:
            sender_email: Email address of the sender
            message_type: 'incoming' or 'outgoing'
            content: Message content
            subject: Email subject
            message_id: Unique message identifier
        """
        if sender_email not in self.conversations:
            self.conversations[sender_email] = []
        
        message = {
            'timestamp': datetime.now().isoformat(),
            'type': message_type,
            'content': content,
            'subject': subject,
            'message_id': message_id
        }
        
        self.conversations[sender_email].append(message)
        
        # Keep only last 20 messages per conversation to prevent memory bloat
        if len(self.conversations[sender_email]) > 20:
            self.conversations[sender_email] = self.conversations[sender_email][-20:]
        
        self._save_conversations()
        logger.info(f"Added {message_type} message to conversation with {sender_email}")
    
    def get_conversation_history(self, sender_email: str, limit: int = 10) -> List[Dict]:
        """
        Get conversation history for a specific sender
        
        Args:
            sender_email: Email address of the sender
            limit: Maximum number of messages to return
            
        Returns:
            List of conversation messages
        """
        if sender_email not in self.conversations:
            return []
        
        messages = self.conversations[sender_email]
        return messages[-limit:] if limit else messages
    
    def get_conversation_context(self, sender_email: str) -> str:
        """
        Get a formatted conversation context for AI processing
        
        Args:
            sender_email: Email address of the sender
            
        Returns:
            Formatted conversation context string
        """
        history = self.get_conversation_history(sender_email, limit=5)
        
        if not history:
            return "No previous conversation history."
        
        context_lines = []
        for msg in history:
            role = "Human" if msg['type'] == 'incoming' else "Alan"
            timestamp = msg['timestamp'][:19]  # Remove microseconds
            context_lines.append(f"[{timestamp}] {role}: {msg['content'][:200]}...")
        
        return "\n".join(context_lines)
    
    def clear_conversation(self, sender_email: str):
        """Clear conversation history for a specific sender"""
        if sender_email in self.conversations:
            del self.conversations[sender_email]
            self._save_conversations()
            logger.info(f"Cleared conversation history for {sender_email}")
    
    def get_all_conversations(self) -> Dict[str, List[Dict]]:
        """Get all conversation histories"""
        return self.conversations.copy()
    
    def get_conversation_stats(self) -> Dict[str, int]:
        """Get statistics about conversations"""
        stats = {
            'total_conversations': len(self.conversations),
            'total_messages': sum(len(conv) for conv in self.conversations.values()),
            'active_conversations': len([conv for conv in self.conversations.values() if conv])
        }
        return stats
