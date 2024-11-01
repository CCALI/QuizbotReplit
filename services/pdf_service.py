import PyPDF2
import io
import os
from datetime import datetime
import streamlit as st

class PDFService:
    def __init__(self):
        self.readings_folder = 'Readings'

    def extract_text_from_pdfs(self) -> str:
        """Extract text from all PDFs in the Readings folder with progress indicator"""
        # Check if cached text exists in session state
        if 'cached_pdf_text' in st.session_state:
            return st.session_state.cached_pdf_text

        all_text = ""
        pdf_files = [f for f in os.listdir(self.readings_folder) if f.endswith('.pdf')]
        
        if not pdf_files:
            return ""

        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, filename in enumerate(pdf_files):
            status_text.text(f"Processing {filename}...")
            file_path = os.path.join(self.readings_folder, filename)
            
            try:
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        all_text += page.extract_text() + "\n"
            except Exception as e:
                st.error(f"Error processing {filename}: {str(e)}")
                continue

            # Update progress
            progress = (idx + 1) / len(pdf_files)
            progress_bar.progress(progress)

        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()

        # Cache the extracted text
        st.session_state.cached_pdf_text = all_text
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
