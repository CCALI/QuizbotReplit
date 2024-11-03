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
        self.chunk_size = 300  # Reduced from 500
        self.extraction_threads = 2  # Reduced from 4
        self.file_cache = {}
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
        text = text.strip()
        return text

    def _process_page(self, page) -> str:
        try:
            # Simplified text extraction
            text = page.extract_text(
                layout=True,
                x_tolerance=3,
                y_tolerance=3
            )
            return text.strip() if text else ""
        except Exception as e:
            print(f"Error processing page: {str(e)}")
            return ""

    def _process_pdf_parallel(self, pdf_path: str) -> Tuple[str, List, List, Dict]:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                # Process pages in smaller batches
                text_chunks = []
                batch_size = 5
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for batch_start in range(0, total_pages, batch_size):
                    batch_end = min(batch_start + batch_size, total_pages)
                    batch_pages = list(range(batch_start, batch_end))
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=self.extraction_threads) as executor:
                        futures = {
                            executor.submit(self._process_page, pdf.pages[i]): i 
                            for i in batch_pages
                        }
                        
                        for future in concurrent.futures.as_completed(futures):
                            page_num = futures[future]
                            try:
                                text = future.result()
                                if text:
                                    text_chunks.append(text)
                            except Exception as e:
                                st.error(f"Error processing page {page_num + 1}: {str(e)}")
                    
                    # Update progress
                    progress = min((batch_end) / total_pages, 1.0)
                    progress_bar.progress(progress)
                    status_text.write(f"Processing pages {batch_start + 1}-{batch_end}/{total_pages}")
                    
                    # Force garbage collection after each batch
                    gc.collect()
                
                progress_bar.empty()
                status_text.empty()
                
                return '\n\n'.join(text_chunks), [], [], {}
                
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
        if not text:
            return []
            
        chunk_size = chunk_size or self.chunk_size
        chunks = []
        current_chunk = []
        current_size = 0
        
        # Simple paragraph-based chunking
        for paragraph in text.split('\n\n'):
            if current_size + len(paragraph) > chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
            current_chunk.append(paragraph)
            current_size += len(paragraph)
            
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
