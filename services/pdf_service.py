import PyPDF2
import io
import os
from datetime import datetime

class PDFService:
    def __init__(self):
        self.readings_folder = 'Readings'

    def save_pdf(self, pdf_file) -> str:
        """Save the uploaded PDF to the Readings folder and return the saved file path"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{pdf_file.name}"
        file_path = os.path.join(self.readings_folder, filename)
        
        with open(file_path, 'wb') as f:
            f.write(pdf_file.getvalue())
        
        return file_path

    def extract_text(self, pdf_file) -> str:
        """Extract text from a PDF file"""
        # Save the PDF first
        file_path = self.save_pdf(pdf_file)
        
        # Then read and extract text
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text

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
