import nltk
from typing import List

class NormaliseSentence:
    def __init__(self, sentence_overlap: int = 1):
        self.overlap = sentence_overlap

    def normalize(self, chunks: List[str]) -> List[str]:
        normalized = []
        prev_sentences = []

        for chunk in chunks:
            sentences = nltk.sent_tokenize(chunk)
            if prev_sentences:
                sentences = prev_sentences[-self.overlap:] + sentences
            normalized.append(" ".join(sentences))
            prev_sentences = sentences
        return normalized
