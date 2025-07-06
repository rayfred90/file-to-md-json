import pytesseract
from PIL import Image
import os
import io
import fitz  # PyMuPDF for PDF to image conversion
from typing import Dict, Any, List
from .base_processor import BaseProcessor

class OCRProcessor(BaseProcessor):
    """Process images and scanned PDFs using OCR (Optical Character Recognition)"""
    
    def __init__(self):
        super().__init__()
        # Configure tesseract path if needed (usually auto-detected on Linux)
        # pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
    
    def process(self, filepath: str) -> Dict[str, Any]:
        """Extract text from image files or scanned PDFs using OCR"""
        result = {
            'text': '',
            'metadata': {},
            'ocr_confidence': None,
            'pages_processed': 0
        }
        
        try:
            # Check if file exists
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")
            
            # Determine file type
            file_extension = filepath.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                result = self._process_pdf_with_ocr(filepath)
            else:
                result = self._process_image_with_ocr(filepath)
                
        except Exception as e:
            result['error'] = str(e)
            result['text'] = f"Error processing file with OCR: {str(e)}"
        
        return result
    
    def _process_image_with_ocr(self, filepath: str) -> Dict[str, Any]:
        """Process a single image file with OCR"""
        result = {
            'text': '',
            'metadata': {},
            'ocr_confidence': None,
            'pages_processed': 1
        }
        
        # Open and process the image
        with Image.open(filepath) as image:
            # Get image metadata
            result['metadata'] = {
                'file_type': 'Image',
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'width': image.width,
                'height': image.height
            }
            
            # Perform OCR
            # Get text with confidence scores
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Extract text
            extracted_text = pytesseract.image_to_string(image, lang='eng')
            
            # Calculate average confidence
            confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
            if confidences:
                result['ocr_confidence'] = sum(confidences) / len(confidences)
            
            # Clean and format the text
            lines = extracted_text.strip().split('\n')
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            
            result['text'] = '\n'.join(cleaned_lines)
            
            # Add OCR metadata
            result['metadata']['total_words'] = len(cleaned_lines)
            result['metadata']['extraction_method'] = 'Tesseract OCR'
            if result['ocr_confidence']:
                result['metadata']['average_confidence'] = f"{result['ocr_confidence']:.2f}%"
        
        return result
    
    def _process_pdf_with_ocr(self, filepath: str) -> Dict[str, Any]:
        """Process a PDF file by converting pages to images and applying OCR"""
        result = {
            'text': '',
            'metadata': {},
            'ocr_confidence': None,
            'pages_processed': 0,
            'pages': []
        }
        
        # Open PDF
        pdf_document = fitz.open(filepath)
        all_text = []
        all_confidences = []
        page_results = []
        
        # Get PDF metadata
        result['metadata'] = {
            'file_type': 'Scanned PDF',
            'total_pages': len(pdf_document),
            'extraction_method': 'PDF to Image + Tesseract OCR'
        }
        
        # Process each page
        for page_num in range(len(pdf_document)):
            try:
                page = pdf_document.load_page(page_num)
                
                # Convert page to image
                # Use higher DPI for better OCR results
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convert to PIL Image
                image = Image.open(io.BytesIO(img_data))
                
                # Perform OCR on this page
                page_text = pytesseract.image_to_string(image, lang='eng')
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                
                # Calculate confidence for this page
                page_confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
                page_confidence = sum(page_confidences) / len(page_confidences) if page_confidences else 0
                
                # Clean page text
                lines = page_text.strip().split('\n')
                cleaned_lines = [line.strip() for line in lines if line.strip()]
                clean_page_text = '\n'.join(cleaned_lines)
                
                if clean_page_text:  # Only add non-empty pages
                    all_text.append(f"--- Page {page_num + 1} ---\n{clean_page_text}")
                    all_confidences.extend(page_confidences)
                    
                    page_results.append({
                        'page_number': page_num + 1,
                        'text': clean_page_text,
                        'confidence': page_confidence,
                        'word_count': len(clean_page_text.split())
                    })
                
                result['pages_processed'] += 1
                
            except Exception as e:
                # Log page processing error but continue with other pages
                page_results.append({
                    'page_number': page_num + 1,
                    'error': str(e),
                    'text': '',
                    'confidence': 0
                })
        
        pdf_document.close()
        
        # Combine all page texts
        result['text'] = '\n\n'.join(all_text)
        result['pages'] = page_results
        
        # Calculate overall confidence
        if all_confidences:
            result['ocr_confidence'] = sum(all_confidences) / len(all_confidences)
            result['metadata']['average_confidence'] = f"{result['ocr_confidence']:.2f}%"
        
        # Add processing statistics
        result['metadata']['pages_with_text'] = len([p for p in page_results if p.get('text')])
        result['metadata']['total_words'] = sum(p.get('word_count', 0) for p in page_results)
        
        return result
    
    def to_markdown(self, content: Dict[str, Any]) -> str:
        """Convert OCR content to markdown"""
        if isinstance(content, str):
            return content
        
        if content.get('text'):
            markdown = "# OCR Extracted Text\n\n"
            
            # Add metadata if available
            if content.get('metadata'):
                markdown += "## Document Information\n\n"
                for key, value in content['metadata'].items():
                    markdown += f"**{key.replace('_', ' ').title()}:** {value}\n\n"
            
            # Add OCR confidence if available
            if content.get('ocr_confidence'):
                markdown += f"**OCR Confidence:** {content['ocr_confidence']:.2f}%\n\n"
            
            # Add page processing info for PDFs
            if content.get('pages_processed'):
                markdown += f"**Pages Processed:** {content['pages_processed']}\n\n"
            
            # Add page-by-page breakdown for PDFs
            if content.get('pages') and len(content['pages']) > 1:
                markdown += "## Page-by-Page Analysis\n\n"
                for page_info in content['pages']:
                    if page_info.get('error'):
                        markdown += f"**Page {page_info['page_number']}:** Error - {page_info['error']}\n\n"
                    else:
                        confidence = page_info.get('confidence', 0)
                        word_count = page_info.get('word_count', 0)
                        markdown += f"**Page {page_info['page_number']}:** {word_count} words, {confidence:.1f}% confidence\n\n"
            
            markdown += "## Extracted Text\n\n"
            markdown += content['text']
            
            return markdown
        
        return "No text extracted from document."
    
    @staticmethod
    def supported_formats():
        """Return list of supported image and document formats"""
        return ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif', '.webp', '.pdf']
    
    def preprocess_image(self, image_path: str, output_path: str = None) -> str:
        """
        Preprocess image for better OCR results
        Returns path to preprocessed image
        """
        try:
            with Image.open(image_path) as image:
                # Convert to grayscale if needed
                if image.mode != 'L':
                    image = image.convert('L')
                
                # Enhance contrast (simple approach)
                # You can add more sophisticated preprocessing here
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.5)  # Increase contrast by 50%
                
                if output_path is None:
                    base_name = os.path.splitext(image_path)[0]
                    output_path = f"{base_name}_preprocessed.png"
                
                image.save(output_path)
                return output_path
                
        except Exception as e:
            raise Exception(f"Error preprocessing image: {str(e)}")
    
    def extract_text_with_confidence_threshold(self, filepath: str, min_confidence: float = 60.0) -> Dict[str, Any]:
        """
        Extract text but filter out words below a confidence threshold
        Useful for improving accuracy on poor quality scans
        """
        try:
            result = self.process(filepath)
            
            if not result.get('text'):
                return result
            
            # Re-process with confidence filtering
            file_extension = filepath.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                # For PDFs, we'd need to reprocess each page individually
                # This is a simplified version
                return result
            else:
                # For images, filter by confidence
                with Image.open(filepath) as image:
                    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                    
                    # Filter words by confidence
                    filtered_words = []
                    for i, conf in enumerate(ocr_data['conf']):
                        if int(conf) >= min_confidence and ocr_data['text'][i].strip():
                            filtered_words.append(ocr_data['text'][i])
                    
                    filtered_text = ' '.join(filtered_words)
                    result['text'] = filtered_text
                    result['metadata']['confidence_threshold'] = min_confidence
                    result['metadata']['words_filtered'] = len([w for w in ocr_data['text'] if w.strip()]) - len(filtered_words)
            
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'text': f"Error processing with confidence threshold: {str(e)}"
            }
