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
import concurrent.futures
import threading
from typing import Dict, List, Tuple
import gc

class PDFService:
    def __init__(self):
        self.readings_folder = 'Readings'
        self.supported_formats = ['.pdf']
        self.math_pattern = re.compile(r'\$.*?\$|\\\[.*?\\\]|\\\(.*?\\\)')
        self.footnote_pattern = re.compile(r'\[\d+\]|\(\d+\)')
        self.file_cache: Dict[str, Tuple] = {}
        self.chunk_size = 500
        self.extraction_threads = 4
        self._cache_lock = threading.Lock()
        
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of a file with memory efficient chunking"""
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

    def _process_page(self, page) -> str:
        """Process a single page with optimized memory usage"""
        try:
            words = page.extract_words(
                keep_blank_chars=True,
                use_text_flow=True,
                x_tolerance=3,
                y_tolerance=3
            )
            
            if not words:
                return ""
                
            current_line = []
            last_y = None
            lines = []
            
            for word in words:
                if last_y is not None and abs(word['top'] - last_y) > 3:
                    if current_line:
                        lines.append(self.clean_text(''.join(current_line)))
                    current_line = []
                    
                current_line.append(word['text'])
                last_y = word['top']
            
            if current_line:
                lines.append(self.clean_text(''.join(current_line)))
            
            return '\n'.join(lines)
        except Exception as e:
            st.error(f"Error processing page: {str(e)}")
            return ""

    def _process_pdf_parallel(self, pdf_path: str) -> Tuple[str, List, List, Dict]:
        """Process PDF pages in parallel with improved memory management"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process pages in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.extraction_threads) as executor:
                    future_to_page = {
                        executor.submit(self._process_page, pdf.pages[i]): i 
                        for i in range(total_pages)
                    }
                    
                    text_chunks = [""] * total_pages
                    completed = 0
                    
                    for future in concurrent.futures.as_completed(future_to_page):
                        page_num = future_to_page[future]
                        try:
                            text_chunks[page_num] = future.result()
                        except Exception as e:
                            st.error(f"Error processing page {page_num + 1}: {str(e)}")
                            text_chunks[page_num] = ""
                            
                        completed += 1
                        progress = completed / total_pages
                        progress_bar.progress(progress)
                        status_text.write(f"Processing page {completed}/{total_pages}")
                        
                        # Force garbage collection periodically
                        if completed % 10 == 0:
                            gc.collect()
                
                progress_bar.empty()
                status_text.empty()
                
                # Extract tables and images in parallel
                tables_future = executor.submit(self.extract_tables, pdf_path)
                images_future = executor.submit(self.extract_images, pdf_path)
                
                tables = tables_future.result()
                images = images_future.result()
                
                # Process footnotes
                footnotes = {}
                footnote_matches = self.footnote_pattern.finditer('\n'.join(text_chunks))
                for match in footnote_matches:
                    footnote_num = match.group()
                    footnotes[footnote_num] = {
                        'page': -1,  # Page number tracking removed for efficiency
                        'text': match.group()
                    }
                
                return '\n'.join(text_chunks), tables, images, footnotes
                
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            return "", [], [], {}

    def extract_text_with_formatting(self, folder_path: str) -> Tuple[str, List, List, Dict]:
        """Extract text from PDFs with improved caching and parallel processing"""
        try:
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
            
            total_files = len(pdf_files)
            overall_progress = st.progress(0)
            file_status = st.empty()
            
            for i, filename in enumerate(pdf_files):
                file_path = os.path.join(folder_path, filename)
                file_status.write(f"Processing {filename} ({i+1}/{total_files})")
                
                try:
                    if os.path.getsize(file_path) == 0:
                        st.warning(f"Skipping empty file: {filename}")
                        continue
                        
                    file_hash = self._calculate_file_hash(file_path)
                    cache_key = f"{file_hash}_{os.path.getsize(file_path)}"
                    
                    # Thread-safe cache access
                    with self._cache_lock:
                        if cache_key in self.file_cache:
                            text, tables, images, footnotes = self.file_cache[cache_key]
                            file_status.write(f"Retrieved {filename} from cache")
                        else:
                            text, tables, images, footnotes = self._process_pdf_parallel(file_path)
                            if text.strip():
                                self.file_cache[cache_key] = (text, tables, images, footnotes)
                            else:
                                st.warning(f"No text content found in {filename}")
                    
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
                
                overall_progress.progress((i + 1) / total_files)
                
                # Periodic cache cleanup to manage memory
                if len(self.file_cache) > 10:
                    with self._cache_lock:
                        oldest_keys = sorted(self.file_cache.keys())[:-10]
                        for key in oldest_keys:
                            del self.file_cache[key]
                    gc.collect()
            
            overall_progress.empty()
            file_status.empty()
            
            if not all_text:
                st.error("No text could be extracted from any PDF files")
                return "", [], [], {}
                
            return '\n'.join(all_text), all_tables, all_images, all_footnotes
            
        except Exception as e:
            st.error(f"Error accessing folder {folder_path}: {str(e)}")
            return "", [], [], {}

    def chunk_text(self, text: str, chunk_size: int = None) -> List[str]:
        """Split text into optimized chunks with improved efficiency"""
        if not text:
            return []
            
        if chunk_size is None:
            chunk_size = self.chunk_size
            
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            # Check for special content more efficiently
            special_content = ('__EQUATION__' in paragraph or 
                             '---' in paragraph or 
                             '|' in paragraph or 
                             '•' in paragraph)
            
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
                        sentence_len = len(sentence)
                        if temp_length + sentence_len > current_chunk_size:
                            if temp_chunk:
                                chunks.append(' '.join(temp_chunk))
                            temp_chunk = [sentence]
                            temp_length = sentence_len
                        else:
                            temp_chunk.append(sentence)
                            temp_length += sentence_len
                    
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
