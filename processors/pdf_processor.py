import pdfplumber
import gc
import time
import os
import base64
import io
from typing import Dict, Any, List, Callable, Optional
from PIL import Image
import fitz  # PyMuPDF for image extraction
from .base_processor import BaseProcessor

class PDFProcessor(BaseProcessor):
    """Process PDF files including scanned PDFs with OCR fallback"""
    
    def __init__(self):
        super().__init__()
        self.progress_callback = None
    
    def set_progress_callback(self, callback: Callable[[int, str], None]):
        """Set a callback function to report progress"""
        self.progress_callback = callback
    
    def _report_progress(self, percentage: int, message: str):
        """Report progress if callback is set"""
        if self.progress_callback:
            self.progress_callback(percentage, message)
    
    def process(self, filepath: str) -> Dict[str, Any]:
        """Extract text, tables, and images from PDF, with OCR fallback for scanned documents"""
        result = {
            'text': '',
            'tables': [],
            'pages': [],
            'images': [],
            'metadata': {},
            'extraction_method': 'text_extraction'
        }
        
        try:
            self._report_progress(5, "Opening PDF file...")
            
            with pdfplumber.open(filepath) as pdf:
                total_pages = len(pdf.pages)
                
                # Check file size and adjust processing strategy
                import os
                file_size = os.path.getsize(filepath)
                file_size_mb = file_size / (1024 * 1024)
                
                self._report_progress(10, f"PDF opened: {total_pages} pages, {file_size_mb:.1f}MB")
                
                # Extract metadata
                if pdf.metadata:
                    result['metadata'] = {
                        'title': pdf.metadata.get('Title', ''),
                        'author': pdf.metadata.get('Author', ''),
                        'subject': pdf.metadata.get('Subject', ''),
                        'creator': pdf.metadata.get('Creator', ''),
                        'pages': total_pages,
                        'file_size_mb': round(file_size_mb, 2)
                    }
                
                # Use streaming approach for large files
                if file_size_mb > 50:  # Files larger than 50MB
                    self._report_progress(12, "Large file detected - using streaming approach...")
                    result = self._process_large_pdf_streaming(pdf, result, total_pages)
                else:
                    result = self._process_standard_pdf(pdf, result, total_pages)
                
                # Extract images from PDF using PyMuPDF
                self._report_progress(87, "Extracting images from PDF...")
                result = self._extract_images(filepath, result)
                
        except Exception as e:
            self._report_progress(95, "PDF processing failed, attempting OCR fallback...")
            # If regular PDF processing fails, try OCR
            try:
                result = self._fallback_to_ocr(filepath, result)
                result['metadata']['fallback_reason'] = f"PDF processing error: {str(e)}"
            except Exception as ocr_error:
                result['error'] = f"PDF processing failed: {str(e)}, OCR fallback failed: {str(ocr_error)}"
                result['text'] = f"Error processing PDF: {str(e)}"
        
        self._report_progress(100, "PDF processing completed")
        return result
    
    def _process_standard_pdf(self, pdf, result: Dict[str, Any], total_pages: int) -> Dict[str, Any]:
        """Process PDF using standard approach for smaller files"""
        full_text = []
        pages_with_text = 0
        total_text_length = 0
        
        for page_num, page in enumerate(pdf.pages, 1):
            progress = 15 + int((page_num / total_pages) * 70)  # 15% to 85%
            self._report_progress(progress, f"Processing page {page_num}/{total_pages}")
            
            page_data = {
                'page_number': page_num,
                'text': '',
                'tables': []
            }
            
            # Extract text
            page_text = page.extract_text()
            if page_text:
                page_text = page_text.strip()
                if page_text:  # Only count non-empty text
                    page_data['text'] = page_text
                    full_text.append(f"--- Page {page_num} ---\n{page_text}")
                    pages_with_text += 1
                    total_text_length += len(page_text)
            
            # Extract tables (skip for very large files to save memory)
            if total_pages < 100:  # Only extract tables for smaller PDFs
                tables = page.extract_tables()
                if tables:
                    for table_idx, table in enumerate(tables):
                        if table:
                            table_data = {
                                'page': page_num,
                                'table_index': table_idx,
                                'data': table
                            }
                            page_data['tables'].append(table_data)
                            result['tables'].append(table_data)
                            
                            # Add table as markdown to text
                            table_md = self._table_to_markdown(table)
                            full_text.append(f"\n--- Table {table_idx + 1} (Page {page_num}) ---\n{table_md}")
            
            result['pages'].append(page_data)
            
            # Force garbage collection every 10 pages for large files
            if page_num % 10 == 0:
                gc.collect()
        
        # Check if we got meaningful text (heuristic for scanned PDFs)
        avg_text_per_page = total_text_length / total_pages if total_pages else 0
        
        self._report_progress(85, "Analyzing extracted content...")
        
        # Smart decision making for large files based on text extraction success
        file_size_mb = result.get('metadata', {}).get('file_size_mb', 0)
        text_extraction_failed = pages_with_text < total_pages * 0.5 or avg_text_per_page < 100
        
        if text_extraction_failed:
            if file_size_mb > 200:
                # For extremely large files, provide guidance
                result['text'] = '\n\n'.join(full_text) if full_text else "This appears to be a scanned PDF with minimal text extraction. OCR was skipped due to file size (>200MB)."
                result['metadata']['pages_with_text'] = pages_with_text
                result['metadata']['avg_text_per_page'] = round(avg_text_per_page, 2)
                result['metadata']['note'] = 'OCR skipped for extremely large file - recommend splitting PDF first'
                result['metadata']['recommendation'] = 'Split this PDF into smaller chunks for OCR processing'
            elif file_size_mb > 100:
                # For large files, use smart OCR approach
                self._report_progress(90, "Large scanned PDF detected - using smart OCR approach...")
                result = self._smart_ocr_for_large_files(pdf.stream.name, result, total_pages)
            else:
                # Normal OCR fallback
                self._report_progress(90, "Low text extraction detected, trying OCR...")
                result = self._fallback_to_ocr(pdf.stream.name, result)
        else:
            result['text'] = '\n\n'.join(full_text)
            result['metadata']['pages_with_text'] = pages_with_text
            result['metadata']['avg_text_per_page'] = round(avg_text_per_page, 2)
        
        return result
    
    def _process_large_pdf_streaming(self, pdf, result: Dict[str, Any], total_pages: int) -> Dict[str, Any]:
        """Process large PDF files using streaming approach to reduce memory usage"""
        self._report_progress(15, "Using streaming approach for large PDF...")
        
        # For very large files, we'll process in smaller chunks
        chunk_size = min(20, max(5, total_pages // 10))  # Process 5-20 pages at a time
        
        full_text = []
        pages_with_text = 0
        total_text_length = 0
        
        for chunk_start in range(0, total_pages, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_pages)
            progress = 15 + int((chunk_start / total_pages) * 65)  # 15% to 80%
            
            self._report_progress(progress, f"Processing chunk {chunk_start // chunk_size + 1}/{(total_pages + chunk_size - 1) // chunk_size} (pages {chunk_start + 1}-{chunk_end})")
            
            # Process this chunk of pages
            chunk_text = []
            for page_idx in range(chunk_start, chunk_end):
                page = pdf.pages[page_idx]
                page_num = page_idx + 1
                
                # Report sub-progress for very large files
                if total_pages > 500 and page_num % 10 == 0:
                    sub_progress = progress + int(((page_idx - chunk_start) / chunk_size) * 5)  # Add up to 5% within chunk
                    self._report_progress(sub_progress, f"Processing page {page_num}/{total_pages}")
                
                page_data = {
                    'page_number': page_num,
                    'text': '',
                    'tables': []  # Skip tables for large files to save memory
                }
                
                # Extract text only (skip tables for large files)
                try:
                    page_text = page.extract_text()
                    if page_text:
                        page_text = page_text.strip()
                        if page_text:
                            page_data['text'] = page_text
                            chunk_text.append(f"--- Page {page_num} ---\n{page_text}")
                            pages_with_text += 1
                            total_text_length += len(page_text)
                except Exception as e:
                    # If individual page processing fails, continue with others
                    page_data['text'] = f"Error processing page {page_num}: {str(e)}"
                
                result['pages'].append(page_data)
            
            # Add chunk text to full text
            full_text.extend(chunk_text)
            
            # Force garbage collection after each chunk
            gc.collect()
            
            # Add a small delay to prevent system overload
            time.sleep(0.05)  # Reduced delay for better performance
        
        # Analyze results
        avg_text_per_page = total_text_length / total_pages if total_pages else 0
        
        self._report_progress(85, "Analyzing extracted content...")
        
        # Smart decision making for large files based on text extraction success
        file_size_mb = result.get('metadata', {}).get('file_size_mb', 0)
        text_extraction_failed = pages_with_text < total_pages * 0.3 or avg_text_per_page < 50
        
        if text_extraction_failed:
            if file_size_mb > 200:
                # For extremely large files (>200MB), ask user for confirmation
                self._report_progress(88, "Very large scanned PDF detected. OCR may take hours...")
                result['text'] = '\n\n'.join(full_text) if full_text else "This appears to be a scanned PDF with minimal text extraction. OCR was skipped due to file size (>200MB)."
                result['metadata']['pages_with_text'] = pages_with_text
                result['metadata']['avg_text_per_page'] = round(avg_text_per_page, 2)
                result['metadata']['processing_method'] = 'text_extraction_only'
                result['metadata']['note'] = 'OCR skipped for extremely large file - recommend splitting PDF first'
                result['metadata']['recommendation'] = 'Split this PDF into smaller chunks for OCR processing'
            elif file_size_mb > 100:
                # For large files (100-200MB), use sample-based OCR decision
                self._report_progress(90, "Large scanned PDF detected - testing OCR on sample pages...")
                result = self._smart_ocr_for_large_files(pdf.stream.name, result, total_pages)
            else:
                # Normal OCR fallback for smaller files
                self._report_progress(90, "Low text extraction detected, trying OCR...")
                result = self._fallback_to_ocr(pdf.stream.name, result)
        else:
            result['text'] = '\n\n'.join(full_text)
            result['metadata']['pages_with_text'] = pages_with_text
            result['metadata']['avg_text_per_page'] = round(avg_text_per_page, 2)
            result['metadata']['processing_method'] = 'streaming'
        
        return result
    
    def _smart_ocr_for_large_files(self, filepath: str, existing_result: Dict[str, Any], total_pages: int) -> Dict[str, Any]:
        """Smart OCR approach for large files - test on sample pages first"""
        try:
            # Import OCR processor here to avoid circular imports
            from .ocr_processor import OCRProcessor
            
            self._report_progress(92, "Testing OCR on sample pages...")
            
            # Test OCR on a small sample of pages (first, middle, last few pages)
            sample_pages = []
            if total_pages <= 10:
                sample_pages = list(range(1, total_pages + 1))
            else:
                # Sample strategy: first 3, middle 3, last 3 pages
                sample_pages.extend([1, 2, 3])  # First pages
                middle = total_pages // 2
                sample_pages.extend([middle - 1, middle, middle + 1])  # Middle pages  
                sample_pages.extend([total_pages - 2, total_pages - 1, total_pages])  # Last pages
                # Remove duplicates and invalid pages
                sample_pages = list(set([p for p in sample_pages if 1 <= p <= total_pages]))
            
            # Test OCR on sample pages
            ocr_processor = OCRProcessor()
            sample_success = 0
            sample_total = len(sample_pages)
            
            for page_num in sample_pages[:5]:  # Test max 5 pages
                try:
                    # Create a temporary single-page PDF for testing
                    import subprocess
                    import tempfile
                    
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                        temp_path = temp_pdf.name
                    
                    # Extract single page using pdftk or similar tool
                    # If pdftk not available, use PyPDF2 as fallback
                    try:
                        subprocess.run(['pdftk', filepath, 'cat', str(page_num), 'output', temp_path], 
                                     check=True, capture_output=True)
                        
                        # Test OCR on this single page
                        page_result = ocr_processor.process(temp_path)
                        if page_result.get('text') and len(page_result['text'].strip()) > 50:
                            sample_success += 1
                        
                        os.unlink(temp_path)
                        
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        # pdftk not available, skip this sample
                        continue
                        
                except Exception:
                    continue
            
            # Decision based on sample results
            success_rate = sample_success / max(sample_total, 1)
            
            if success_rate > 0.5:  # If OCR works well on samples
                self._report_progress(95, f"OCR successful on samples ({success_rate:.0%}). Processing full document...")
                
                # For large files, use chunked OCR processing
                result = self._chunked_ocr_processing(filepath, existing_result, total_pages)
            else:
                self._report_progress(95, f"OCR test failed on samples ({success_rate:.0%}). Using text extraction only...")
                
                # OCR doesn't seem to work well, use text extraction
                existing_result['text'] = existing_result.get('text', 'OCR test failed - this PDF may not be suitable for OCR processing.')
                existing_result['metadata']['ocr_test_result'] = f'Failed ({success_rate:.0%} success rate on sample pages)'
                existing_result['metadata']['recommendation'] = 'This PDF may not be scannable or may require different OCR settings'
                
            return existing_result
            
        except Exception as e:
            existing_result['error'] = f"Smart OCR failed: {str(e)}"
            return existing_result
    
    def _chunked_ocr_processing(self, filepath: str, existing_result: Dict[str, Any], total_pages: int) -> Dict[str, Any]:
        """Process large PDF with OCR in smaller chunks"""
        try:
            from .ocr_processor import OCRProcessor
            import subprocess
            import tempfile
            
            ocr_processor = OCRProcessor()
            chunk_size = 20  # Process 20 pages at a time
            all_text = []
            processed_pages = 0
            
            for chunk_start in range(1, total_pages + 1, chunk_size):
                chunk_end = min(chunk_start + chunk_size - 1, total_pages)
                
                progress = 95 + int((processed_pages / total_pages) * 5)  # 95% to 100%
                self._report_progress(progress, f"OCR processing pages {chunk_start}-{chunk_end}/{total_pages}")
                
                try:
                    # Create temporary PDF chunk
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                        temp_path = temp_pdf.name
                    
                    # Extract chunk using pdftk
                    page_range = f"{chunk_start}-{chunk_end}" if chunk_end > chunk_start else str(chunk_start)
                    subprocess.run(['pdftk', filepath, 'cat', page_range, 'output', temp_path], 
                                 check=True, capture_output=True)
                    
                    # OCR the chunk
                    chunk_result = ocr_processor.process(temp_path)
                    if chunk_result.get('text'):
                        all_text.append(f"--- Pages {chunk_start}-{chunk_end} ---\n{chunk_result['text']}")
                    
                    processed_pages += (chunk_end - chunk_start + 1)
                    
                    # Clean up
                    os.unlink(temp_path)
                    
                    # Add delay to prevent system overload
                    time.sleep(0.5)
                    
                except subprocess.CalledProcessError:
                    # If chunk processing fails, skip this chunk
                    all_text.append(f"--- Pages {chunk_start}-{chunk_end} ---\nError: Could not process this chunk")
                    processed_pages += (chunk_end - chunk_start + 1)
                    continue
            
            # Combine results
            existing_result['text'] = '\n\n'.join(all_text)
            existing_result['extraction_method'] = 'chunked_ocr'
            existing_result['metadata']['extraction_method'] = 'Chunked OCR (Large Scanned PDF)'
            existing_result['metadata']['pages_processed'] = processed_pages
            existing_result['metadata']['processing_method'] = 'chunked_ocr_large_file'
            
            return existing_result
            
        except Exception as e:
            # Fallback to regular OCR if chunked processing fails
            existing_result['text'] = "Chunked OCR processing failed. This PDF may be too large or complex for OCR."
            existing_result['error'] = f"Chunked OCR failed: {str(e)}"
            existing_result['metadata']['fallback_reason'] = str(e)
            return existing_result
    
    def _fallback_to_ocr(self, filepath: str, existing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to OCR processing for scanned PDFs"""
        try:
            # Import OCR processor here to avoid circular imports
            from .ocr_processor import OCRProcessor
            
            ocr_processor = OCRProcessor()
            ocr_result = ocr_processor.process(filepath)
            
            # Merge OCR result with existing result
            existing_result['text'] = ocr_result.get('text', '')
            existing_result['extraction_method'] = 'ocr_fallback'
            existing_result['ocr_confidence'] = ocr_result.get('ocr_confidence')
            existing_result['pages_processed'] = ocr_result.get('pages_processed', 0)
            
            # Update metadata
            if 'metadata' not in existing_result:
                existing_result['metadata'] = {}
            
            existing_result['metadata']['extraction_method'] = 'OCR (Scanned PDF)'
            if ocr_result.get('ocr_confidence'):
                existing_result['metadata']['ocr_confidence'] = f"{ocr_result['ocr_confidence']:.2f}%"
            
            # Merge OCR pages info if available
            if ocr_result.get('pages'):
                existing_result['ocr_pages'] = ocr_result['pages']
            
            return existing_result
            
        except Exception as e:
            existing_result['error'] = f"OCR fallback failed: {str(e)}"
            return existing_result
    
    def _extract_images(self, filepath: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract images from PDF using PyMuPDF"""
        try:
            pdf_document = fitz.open(filepath)
            images_extracted = 0
            
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Get the XREF of the image
                        xref = img[0]
                        
                        # Extract the image
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Convert to PIL Image for processing
                        image = Image.open(io.BytesIO(image_bytes))
                        
                        # Convert to base64 for storage/transmission
                        buffered = io.BytesIO()
                        # Convert to RGB if necessary (for JPEG compatibility)
                        if image.mode in ('RGBA', 'LA'):
                            # Create a white background
                            background = Image.new('RGB', image.size, (255, 255, 255))
                            if image.mode == 'RGBA':
                                background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                            else:  # LA mode
                                background.paste(image, mask=image.split()[-1])
                            image = background
                        elif image.mode not in ('RGB', 'L'):
                            image = image.convert('RGB')
                        
                        # Save as JPEG for consistency
                        image.save(buffered, format="JPEG", quality=85)
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        # Store image information
                        image_info = {
                            'page_number': page_num + 1,
                            'image_index': img_index,
                            'format': 'JPEG',  # Normalized format
                            'original_format': image_ext,
                            'width': image.width,
                            'height': image.height,
                            'size_bytes': len(image_bytes),
                            'base64_data': img_str,
                            'filename': f"page_{page_num + 1}_image_{img_index + 1}.jpg",
                            'relative_path': None  # Will be set when saved to document folder
                        }
                        
                        result['images'].append(image_info)
                        images_extracted += 1
                        
                        # Limit number of images to prevent memory issues
                        if images_extracted >= 50:  # Max 50 images
                            break
                            
                    except Exception as e:
                        # Skip problematic images but continue processing
                        continue
                
                if images_extracted >= 50:
                    break
            
            pdf_document.close()
            
            # Update metadata
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['images_extracted'] = images_extracted
            
            if images_extracted > 0:
                self._report_progress(89, f"Extracted {images_extracted} images from PDF")
            
            return result
            
        except Exception as e:
            # If image extraction fails, continue without images
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['image_extraction_error'] = str(e)
            result['metadata']['images_extracted'] = 0
            return result
    
    def _table_to_markdown(self, table: List[List[str]]) -> str:
        """Convert table data to markdown format"""
        if not table or not table[0]:
            return ""
        
        markdown = ""
        
        # Header row
        if table[0]:
            headers = [str(cell) if cell else "" for cell in table[0]]
            markdown += "| " + " | ".join(headers) + " |\n"
            markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        # Data rows
        for row in table[1:]:
            if row:
                cells = [str(cell) if cell else "" for cell in row]
                # Pad row to match header length
                while len(cells) < len(headers):
                    cells.append("")
                markdown += "| " + " | ".join(cells) + " |\n"
        
        return markdown
    
    def to_markdown(self, content: Dict[str, Any]) -> str:
        """Convert PDF content to markdown"""
        if isinstance(content, str):
            return content
        
        markdown = ""
        
        # Add metadata
        if content.get('metadata'):
            metadata = content['metadata']
            markdown += "# Document Information\n\n"
            for key, value in metadata.items():
                if value:
                    markdown += f"**{key.replace('_', ' ').title()}:** {value}\n\n"
        
        # Add extraction method info
        if content.get('extraction_method'):
            method = content['extraction_method']
            if method == 'ocr_fallback':
                markdown += "**Processing Method:** OCR (Scanned PDF - text extraction failed)\n\n"
            else:
                markdown += "**Processing Method:** Direct text extraction\n\n"
        
        # Add OCR confidence if available
        if content.get('ocr_confidence'):
            markdown += f"**OCR Confidence:** {content['ocr_confidence']:.2f}%\n\n"
        
        # Add OCR page analysis for scanned PDFs
        if content.get('ocr_pages') and len(content['ocr_pages']) > 1:
            markdown += "## OCR Page Analysis\n\n"
            for page_info in content['ocr_pages']:
                if page_info.get('error'):
                    markdown += f"**Page {page_info['page_number']}:** Error - {page_info['error']}\n\n"
                else:
                    confidence = page_info.get('confidence', 0)
                    word_count = page_info.get('word_count', 0)
                    markdown += f"**Page {page_info['page_number']}:** {word_count} words, {confidence:.1f}% confidence\n\n"
        
        # Add images information
        if content.get('images') and len(content['images']) > 0:
            markdown += "## Images Extracted\n\n"
            markdown += f"**Total Images:** {len(content['images'])}\n\n"
            
            for img in content['images'][:10]:  # Show details for first 10 images
                markdown += f"### Image {img['image_index']} (Page {img['page_number']})\n"
                markdown += f"- **Filename:** {img['filename']}\n"
                markdown += f"- **Format:** {img['format']} (Original: {img['original_format']})\n"
                markdown += f"- **Dimensions:** {img['width']} x {img['height']} pixels\n"
                markdown += f"- **Size:** {img['size_bytes']:,} bytes\n\n"
            
            if len(content['images']) > 10:
                markdown += f"*... and {len(content['images']) - 10} more images*\n\n"
        
        # Add main text content
        if content.get('text'):
            markdown += "# Content\n\n"
            markdown += content['text']
        
        return markdown
