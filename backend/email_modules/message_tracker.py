import json
import os
import logging
from typing import List

logger = logging.getLogger(__name__)


class MessageTracker:
    def __init__(self, processed_messages_file: str = "processed_messages.json"):
        self.processed_messages_file = processed_messages_file

    def load_processed_ids(self) -> List[str]:
        """Load processed message IDs from JSON file"""
        try:
            if os.path.exists(self.processed_messages_file):
                with open(self.processed_messages_file, "r") as f:
                    data = json.load(f)
                    return data.get("processed_ids", [])
            return []
        except Exception as e:
            logger.error(f"Error loading processed IDs: {e}")
            return []

    def save_processed_id(self, message_id: str):
        """Save processed message ID to JSON file"""
        try:
            processed_ids = self.load_processed_ids()
            if message_id not in processed_ids:
                processed_ids.append(message_id)

                data = {"processed_ids": processed_ids}
                with open(self.processed_messages_file, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Saved processed message ID: {message_id}")
        except Exception as e:
            logger.error(f"Error saving processed ID: {e}")
