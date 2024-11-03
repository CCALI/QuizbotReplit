import os
import pdfplumber
import streamlit as st
import re
import concurrent.futures
import threading
import hashlib
from functools import lru_cache
from typing import Dict, List, Tuple
import gc

class PDFService:
    def __init__(self):
        self.readings_folder = 'Readings'
        self.supported_formats = ['.pdf']
        self.chunk_size = 500
        self.extraction_threads = 4
        self.file_cache: Dict[str, str] = {}
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
                
                combined_text = '\n'.join(text_chunks)
                return combined_text, [], [], {}  # Return empty lists for tables/images/footnotes
                
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            return "", [], [], {}

    def extract_text_with_formatting(self, folder_path: str) -> Tuple[str, List, List, Dict]:
        try:
            if not os.path.exists(folder_path):
                st.error(f"Readings folder not found: {folder_path}")
                return "", [], [], {}
                
            pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
            if not pdf_files:
                st.error("No PDF files found in Readings folder")
                return "", [], [], {}
            
            all_text = []
            for filename in pdf_files:
                file_path = os.path.join(folder_path, filename)
                try:
                    # Skip empty files
                    if os.path.getsize(file_path) == 0:
                        st.warning(f"Skipping empty file: {filename}")
                        continue
                        
                    # Check cache
                    file_hash = self._calculate_file_hash(file_path)
                    cache_key = f"{file_hash}_{os.path.getsize(file_path)}"
                    
                    with self._cache_lock:
                        if cache_key in self.file_cache:
                            text = self.file_cache[cache_key]
                            st.info(f"Retrieved {filename} from cache")
                        else:
                            text, _, _, _ = self._process_pdf_parallel(file_path)
                            if text.strip():
                                self.file_cache[cache_key] = text
                            else:
                                st.warning(f"No text content found in {filename}")
                                continue
                    
                    all_text.append(f"\n=== Document: {filename} ===\n")
                    all_text.append(text)
                    
                    # Periodic cache cleanup
                    if len(self.file_cache) > 10:
                        with self._cache_lock:
                            oldest_keys = sorted(self.file_cache.keys())[:-10]
                            for key in oldest_keys:
                                del self.file_cache[key]
                        gc.collect()
                        
                except Exception as e:
                    st.error(f"Error processing {filename}: {str(e)}")
                    continue
            
            if not all_text:
                st.error("No text could be extracted from any PDF files")
                return "", [], [], {}
                
            return '\n'.join(all_text), [], [], {}
            
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
            # Simple length check for splitting
            if current_length + len(paragraph) > chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Handle long paragraphs
                if len(paragraph) > chunk_size:
                    words = paragraph.split()
                    temp_chunk = []
                    temp_length = 0
                    
                    for word in words:
                        if temp_length + len(word) > chunk_size:
                            if temp_chunk:
                                chunks.append(' '.join(temp_chunk))
                            temp_chunk = [word]
                            temp_length = len(word)
                        else:
                            temp_chunk.append(word)
                            temp_length += len(word) + 1
                    
                    if temp_chunk:
                        chunks.append(' '.join(temp_chunk))
                else:
                    current_chunk = [paragraph]
                    current_length = len(paragraph)
            else:
                current_chunk.append(paragraph)
                current_length += len(paragraph) + 2
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
