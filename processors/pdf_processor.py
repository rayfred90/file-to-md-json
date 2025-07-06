import pdfplumber
from typing import Dict, Any, List
from .base_processor import BaseProcessor

class PDFProcessor(BaseProcessor):
    """Process PDF files including scanned PDFs with OCR fallback"""
    
    def process(self, filepath: str) -> Dict[str, Any]:
        """Extract text and tables from PDF, with OCR fallback for scanned documents"""
        result = {
            'text': '',
            'tables': [],
            'pages': [],
            'metadata': {},
            'extraction_method': 'text_extraction'
        }
        
        try:
            with pdfplumber.open(filepath) as pdf:
                # Extract metadata
                if pdf.metadata:
                    result['metadata'] = {
                        'title': pdf.metadata.get('Title', ''),
                        'author': pdf.metadata.get('Author', ''),
                        'subject': pdf.metadata.get('Subject', ''),
                        'creator': pdf.metadata.get('Creator', ''),
                        'pages': len(pdf.pages)
                    }
                
                full_text = []
                pages_with_text = 0
                total_text_length = 0
                
                for page_num, page in enumerate(pdf.pages, 1):
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
                    
                    # Extract tables
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
                
                # Check if we got meaningful text (heuristic for scanned PDFs)
                avg_text_per_page = total_text_length / len(pdf.pages) if pdf.pages else 0
                
                # If very little text extracted, try OCR fallback
                if pages_with_text < len(pdf.pages) * 0.5 or avg_text_per_page < 100:
                    result = self._fallback_to_ocr(filepath, result)
                else:
                    result['text'] = '\n\n'.join(full_text)
                    result['metadata']['pages_with_text'] = pages_with_text
                    result['metadata']['avg_text_per_page'] = avg_text_per_page
                
        except Exception as e:
            # If regular PDF processing fails, try OCR
            try:
                result = self._fallback_to_ocr(filepath, result)
                result['metadata']['fallback_reason'] = f"PDF processing error: {str(e)}"
            except Exception as ocr_error:
                result['error'] = f"PDF processing failed: {str(e)}, OCR fallback failed: {str(ocr_error)}"
                result['text'] = f"Error processing PDF: {str(e)}"
        
        return result
    
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
        
        # Add main text content
        if content.get('text'):
            markdown += "# Content\n\n"
            markdown += content['text']
        
        return markdown
