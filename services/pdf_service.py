import PyPDF2
import pdfplumber
import io
import os
from datetime import datetime
import streamlit as st
from bs4 import BeautifulSoup
import re
import fitz  # PyMuPDF for better PDF handling
import numpy as np
from PIL import Image
import hashlib
from functools import lru_cache

class PDFService:
    def __init__(self):
        self.readings_folder = 'Readings'
        self.supported_formats = ['.pdf']
        self.math_pattern = re.compile(r'\$.*?\$|\\\[.*?\\\]|\\\(.*?\\\)')
        self.footnote_pattern = re.compile(r'\[\d+\]|\(\d+\)')
        self.cache = {}
        self.chunk_size = 500  # Reduced chunk size as requested
        
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @lru_cache(maxsize=20)
    def clean_text(self, text: str) -> str:
        """Clean and preprocess extracted text with caching"""
        if not text:
            return ""
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'(?<=\n)\s*[•∙◦○●]\s*', '• ', text)
        text = re.sub(r'(?<=\n)\s*(\d+\.|\w+\.)\s+', r'\1 ', text)
        text = text.replace('|', 'I').replace('0', 'O')
        return text.strip()

    def extract_equations(self, text: str) -> tuple:
        """Extract and preserve mathematical equations"""
        equations = self.math_pattern.findall(text)
        text_with_placeholders = self.math_pattern.sub('__EQUATION__', text)
        return text_with_placeholders, equations

    def restore_equations(self, text: str, equations: list) -> str:
        """Restore equations from placeholders"""
        for equation in equations:
            text = text.replace('__EQUATION__', equation, 1)
        return text

    def extract_tables(self, pdf_path: str) -> list:
        """Extract tables with support for merged cells"""
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    found_tables = page.extract_tables(
                        table_settings={
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "intersection_x_tolerance": 3,
                            "intersection_y_tolerance": 3,
                            "snap_x_tolerance": 3,
                            "snap_y_tolerance": 3,
                            "join_tolerance": 3,
                            "edge_min_length": 3,
                            "min_words_vertical": 3,
                            "min_words_horizontal": 1,
                        }
                    )
                    
                    if found_tables:
                        for table in found_tables:
                            processed_table = self._process_merged_cells(table)
                            tables.append(processed_table)
                            
        except Exception as e:
            st.error(f"Error extracting tables: {str(e)}")
        return tables

    def _process_merged_cells(self, table: list) -> list:
        """Handle merged cells in tables"""
        if not table:
            return table
            
        processed = []
        for i, row in enumerate(table):
            processed_row = []
            for j, cell in enumerate(row):
                if cell is None and i > 0:
                    processed_row.append(table[i-1][j])
                else:
                    processed_row.append(cell or '')
            processed.append(processed_row)
        return processed

    def extract_images(self, pdf_path: str) -> list:
        """Extract and process images from PDF"""
        images = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_data = base_image["image"]
                    
                    image = Image.open(io.BytesIO(image_data))
                    images.append({
                        'page': page_num + 1,
                        'index': img_index,
                        'image': image
                    })
                    
        except Exception as e:
            st.error(f"Error extracting images: {str(e)}")
        return images

    def extract_text_with_formatting(self, folder_path: str) -> tuple:
        """Extract text from PDFs with progress tracking and caching"""
        try:
            progress_placeholder = st.empty()
            progress_bar = progress_placeholder.progress(0)
            status_text = st.empty()
            
            if not os.path.exists(folder_path):
                st.error(f"Readings folder not found: {folder_path}")
                return "", [], [], {}
                
            pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
            if not pdf_files:
                st.error("No PDF files found in Readings folder")
                return "", [], [], {}
            
            all_text = []
            all_tables = []
            all_images = []
            all_footnotes = {}
            
            for i, filename in enumerate(pdf_files):
                status_text.write(f"Processing {filename}...")
                file_path = os.path.join(folder_path, filename)
                progress = (i + 1) / len(pdf_files)
                progress_bar.progress(progress)
                
                try:
                    if os.path.getsize(file_path) == 0:
                        st.warning(f"Skipping empty file: {filename}")
                        continue
                        
                    file_hash = self._calculate_file_hash(file_path)
                    cache_key = f"{file_hash}_{os.path.getsize(file_path)}"
                    
                    if cache_key in self.cache:
                        text, tables, images, footnotes = self.cache[cache_key]
                        status_text.write(f"Retrieved {filename} from cache")
                    else:
                        text, tables, images, footnotes = self._extract_single_pdf(file_path)
                        if not text.strip():
                            st.warning(f"No text content found in {filename}")
                        else:
                            self.cache[cache_key] = (text, tables, images, footnotes)
                    
                    all_text.append(f"\n=== Document: {filename} ===\n")
                    all_text.append(text)
                    all_tables.extend(tables)
                    all_images.extend(images)
                    all_footnotes.update({
                        f"{filename}:{k}": v for k, v in footnotes.items()
                    })
                    
                except Exception as e:
                    st.error(f"Error processing {filename}: {str(e)}")
                    continue
            
            progress_placeholder.empty()
            status_text.empty()
            
            if not all_text:
                st.error("No text could be extracted from any PDF files")
                return "", [], [], {}
                
            return '\n'.join(all_text), all_tables, all_images, all_footnotes
            
        except Exception as e:
            st.error(f"Error accessing folder {folder_path}: {str(e)}")
            return "", [], [], {}

    def _process_line(self, line: str) -> str:
        """Process a line of text, handling special formatting"""
        line_with_placeholders, equations = self.extract_equations(line)
        cleaned_line = self.clean_text(line_with_placeholders)
        final_line = self.restore_equations(cleaned_line, equations)
        return final_line

    def _extract_single_pdf(self, pdf_path: str) -> tuple:
        """Extract content from a single PDF with optimized processing"""
        text_content = []
        tables = []
        images = []
        footnotes = {}
        
        try:
            tables = self.extract_tables(pdf_path)
            images = self.extract_images(pdf_path)
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    words = page.extract_words(
                        keep_blank_chars=True,
                        use_text_flow=True,
                        x_tolerance=3,
                        y_tolerance=3
                    )
                    
                    if not words:
                        continue
                    
                    current_line = []
                    last_y = None
                    
                    for word in words:
                        if last_y is not None and abs(word['top'] - last_y) > 3:
                            processed_line = self._process_line(''.join(current_line))
                            if processed_line:
                                text_content.append(processed_line)
                            current_line = []
                        
                        footnote_match = self.footnote_pattern.match(word['text'])
                        if footnote_match:
                            footnote_num = footnote_match.group()
                            footnotes[footnote_num] = {
                                'page': page_num + 1,
                                'text': word['text']
                            }
                        
                        current_line.append(word['text'])
                        last_y = word['top']
                    
                    if current_line:
                        processed_line = self._process_line(''.join(current_line))
                        if processed_line:
                            text_content.append(processed_line)
            
            return '\n'.join(text_content), tables, images, footnotes
        
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            return "", [], [], {}

    def chunk_text(self, text: str, chunk_size: int = None) -> list:
        """Split text into optimized chunks"""
        if not text:
            return []
            
        if chunk_size is None:
            chunk_size = self.chunk_size
            
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            special_content = any(marker in paragraph for marker in 
                               ['__EQUATION__', '---', '|', '•'])
            
            current_chunk_size = chunk_size // 2 if special_content else chunk_size
            
            if special_content or len(paragraph) > current_chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                if len(paragraph) > current_chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    temp_chunk = []
                    temp_length = 0
                    
                    for sentence in sentences:
                        if temp_length + len(sentence) > current_chunk_size:
                            if temp_chunk:
                                chunks.append(' '.join(temp_chunk))
                            temp_chunk = [sentence]
                            temp_length = len(sentence)
                        else:
                            temp_chunk.append(sentence)
                            temp_length += len(sentence)
                    
                    if temp_chunk:
                        chunks.append(' '.join(temp_chunk))
                else:
                    chunks.append(paragraph)
            
            elif current_length + len(paragraph) + 2 > chunk_size:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_length = len(paragraph)
            else:
                current_chunk.append(paragraph)
                current_length += len(paragraph) + 2
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks

    def format_tables_as_text(self, tables: list) -> str:
        """Convert extracted tables to formatted text"""
        if not tables:
            return ""
        
        formatted_tables = []
        for table in tables:
            if not table:
                continue
            
            col_widths = [max(len(str(cell)) for cell in col) 
                         for col in zip(*table)]
            
            header_sep = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
            
            formatted_table = [header_sep]
            for i, row in enumerate(table):
                formatted_row = '|' + '|'.join(
                    f' {str(cell):<{width}} ' 
                    for cell, width in zip(row, col_widths)
                ) + '|'
                formatted_table.append(formatted_row)
                
                if i == 0 or i == len(table) - 1:
                    formatted_table.append(header_sep)
                
            formatted_tables.append('\n'.join(formatted_table))
        
        return '\n\n'.join(formatted_tables)