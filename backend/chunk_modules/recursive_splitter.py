from langchain_text_splitters import RecursiveCharacterTextSplitter

class RecursiveSplitter:
    def __init__(self, chunk_size=1000, overlap=200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " "],
        )

    def split(self, text: str):
        return self.splitter.split_text(text)
    