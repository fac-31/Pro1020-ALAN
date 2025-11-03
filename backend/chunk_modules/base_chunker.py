from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        if metadata is None:
            metadata = {}
        """Return a list of {'text': str, 'metadata': dict} chunks."""
        pass
