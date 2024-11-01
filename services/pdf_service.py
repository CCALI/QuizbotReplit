import PyPDF2
import pdfplumber
import io
import os
from datetime import datetime
import streamlit as st
from bs4 import BeautifulSoup
import re

class PDFService:
    def __init__(self):
        self.readings_folder = 'Readings'
        self.supported_formats = ['.pdf']

    def clean_text(self, text: str) -> str:
        """Clean and preprocess extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers
        text = re.sub(r'\b\d+\b(?:\s*\|\s*Page)?\s*$', '', text, flags=re.MULTILINE)
        # Fix common OCR errors
        text = text.replace('|', 'I').replace('0', 'O')
        return text.strip()

    def extract_tables(self, pdf_path: str) -> list:
        """Extract tables from PDF"""
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
        except Exception as e:
            st.warning(f"Could not extract tables from {pdf_path}: {str(e)}")
        return tables

    def extract_metadata(self, pdf_path: str) -> dict:
        """Extract PDF metadata"""
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                metadata = reader.metadata
                return {
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creation_date': metadata.get('/CreationDate', ''),
                    'page_count': len(reader.pages)
                }
        except Exception as e:
            st.warning(f"Could not extract metadata from {pdf_path}: {str(e)}")
            return {}

    def extract_text_with_formatting(self, pdf_path: str) -> tuple:
        """Extract text while preserving formatting"""
        text_content = []
        tables = []
        
        try:
            # Extract tables first
            tables = self.extract_tables(pdf_path)
            
            # Extract text with formatting
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Extract text with position information
                    words = page.extract_words(
                        keep_blank_chars=True,
                        use_text_flow=True,
                        x_tolerance=3,
                        y_tolerance=3
                    )
                    
                    # Group words by lines
                    current_line = []
                    last_y = None
                    
                    for word in words:
                        if last_y is None:
                            current_line.append(word['text'])
                        elif abs(word['top'] - last_y) > 3:  # New line
                            text_content.append(' '.join(current_line))
                            current_line = [word['text']]
                        else:
                            current_line.append(word['text'])
                        
                        last_y = word['top']
                    
                    if current_line:
                        text_content.append(' '.join(current_line))
                    
                    # Add paragraph break
                    text_content.append('\n')
            
            return '\n'.join(text_content), tables
        
        except Exception as e:
            st.error(f"Error processing {pdf_path}: {str(e)}")
            return "", []

    def format_tables_as_text(self, tables: list) -> str:
        """Convert extracted tables to formatted text"""
        if not tables:
            return ""
        
        formatted_tables = []
        for table in tables:
            if not table:
                continue
            
            # Remove empty cells and clean data
            cleaned_table = [
                [str(cell).strip() if cell is not None else '' for cell in row]
                for row in table
            ]
            
            # Calculate column widths
            col_widths = [
                max(len(str(row[i])) for row in cleaned_table)
                for i in range(len(cleaned_table[0]))
            ]
            
            # Format as text
            table_str = ""
            for row in cleaned_table:
                row_str = " | ".join(
                    str(cell).ljust(width) for cell, width in zip(row, col_widths)
                )
                table_str += row_str + "\n"
                table_str += "-" * len(row_str) + "\n"
            
            formatted_tables.append(table_str)
        
        return "\n\n".join(formatted_tables)

    def extract_text_from_pdfs(self) -> str:
        """Extract text from all PDFs in the Readings folder with progress indicator"""
        # Check if cached text exists in session state
        if 'cached_pdf_text' in st.session_state:
            return st.session_state.cached_pdf_text

        all_text = []
        pdf_files = [f for f in os.listdir(self.readings_folder) 
                    if f.endswith('.pdf')]
        
        if not pdf_files:
            return ""

        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, filename in enumerate(pdf_files):
            status_text.text(f"Processing {filename}...")
            file_path = os.path.join(self.readings_folder, filename)
            
            try:
                # Extract metadata
                metadata = self.extract_metadata(file_path)
                if metadata.get('title'):
                    all_text.append(f"Document: {metadata['title']}\n")
                
                # Extract text and tables
                text, tables = self.extract_text_with_formatting(file_path)
                
                # Clean and process the text
                cleaned_text = self.clean_text(text)
                all_text.append(cleaned_text)
                
                # Format and append tables if any
                if tables:
                    formatted_tables = self.format_tables_as_text(tables)
                    all_text.append("\nExtracted Tables:\n" + formatted_tables)
                
                all_text.append("\n" + "="*50 + "\n")  # Document separator
                
            except Exception as e:
                st.error(f"Error processing {filename}: {str(e)}")
                continue

            # Update progress
            progress = (idx + 1) / len(pdf_files)
            progress_bar.progress(progress)

        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()

        # Combine all text
        final_text = "\n".join(all_text)
        
        # Cache the extracted text
        st.session_state.cached_pdf_text = final_text
        return final_text

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 2000) -> list:
        """Split text into manageable chunks while preserving context"""
        # Split text into paragraphs
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            # If a single paragraph is longer than chunk_size, split it
            if len(paragraph) > chunk_size:
                words = paragraph.split()
                temp_chunk = []
                temp_length = 0
                
                for word in words:
                    word_length = len(word) + 1  # +1 for space
                    if temp_length + word_length > chunk_size:
                        chunks.append(' '.join(temp_chunk))
                        temp_chunk = [word]
                        temp_length = word_length
                    else:
                        temp_chunk.append(word)
                        temp_length += word_length
                
                if temp_chunk:
                    chunks.append(' '.join(temp_chunk))
            
            # For normal paragraphs
            elif current_length + len(paragraph) + 2 > chunk_size:  # +2 for newlines
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_length = len(paragraph)
            else:
                current_chunk.append(paragraph)
                current_length += len(paragraph) + 2
        
        # Add any remaining content
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
