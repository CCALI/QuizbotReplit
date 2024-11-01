import PyPDF2
import io
import os
from datetime import datetime

class PDFService:
    def __init__(self):
        self.readings_folder = 'Readings'

    def extract_text_from_pdfs(self) -> str:
        """Extract text from all PDFs in the Readings folder"""
        all_text = ""
        for filename in os.listdir(self.readings_folder):
            if filename.endswith('.pdf'):
                file_path = os.path.join(self.readings_folder, filename)
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        all_text += page.extract_text() + "\n"
        return all_text

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 2000) -> list:
        """Split text into manageable chunks for API processing"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_length += len(word) + 1
            if current_length > chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        return chunks
