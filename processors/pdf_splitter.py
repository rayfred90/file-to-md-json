#!/usr/bin/env python3
"""
PDF Splitter for Large Scanned Documents
This utility helps split large scanned PDFs into smaller chunks for efficient OCR processing.
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

def check_pdftk():
    """Check if pdftk is available"""
    try:
        subprocess.run(['pdftk', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_pdftk():
    """Install pdftk"""
    print("📦 pdftk not found. Installing...")
    try:
        subprocess.run(['sudo', 'apt', 'update'], check=True)
        subprocess.run(['sudo', 'apt', 'install', '-y', 'pdftk'], check=True)
        print("✅ pdftk installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install pdftk. Please install manually:")
        print("   sudo apt update && sudo apt install pdftk")
        return False

def get_pdf_page_count(pdf_path):
    """Get the number of pages in a PDF"""
    try:
        result = subprocess.run(['pdftk', pdf_path, 'dump_data'], 
                              capture_output=True, text=True, check=True)
        
        for line in result.stdout.split('\n'):
            if line.startswith('NumberOfPages:'):
                return int(line.split(':')[1].strip())
        return 0
    except:
        # Fallback using PyPDF2 if available
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return len(reader.pages)
        except:
            return 0

def split_pdf(input_path, output_dir, chunk_size=50, prefix="chunk"):
    """Split PDF into smaller chunks"""
    
    if not os.path.exists(input_path):
        print(f"❌ Input file not found: {input_path}")
        return False
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Get total pages
    total_pages = get_pdf_page_count(input_path)
    if total_pages == 0:
        print("❌ Could not determine PDF page count")
        return False
    
    print(f"📄 PDF has {total_pages} pages")
    print(f"✂️  Splitting into chunks of {chunk_size} pages each")
    
    chunk_num = 1
    split_files = []
    
    for start_page in range(1, total_pages + 1, chunk_size):
        end_page = min(start_page + chunk_size - 1, total_pages)
        
        output_file = os.path.join(output_dir, f"{prefix}_{chunk_num:03d}_pages_{start_page}-{end_page}.pdf")
        
        try:
            if start_page == end_page:
                page_range = str(start_page)
            else:
                page_range = f"{start_page}-{end_page}"
            
            print(f"🔧 Creating chunk {chunk_num}: pages {start_page}-{end_page}")
            
            subprocess.run(['pdftk', input_path, 'cat', page_range, 'output', output_file], 
                          check=True, capture_output=True)
            
            split_files.append(output_file)
            chunk_num += 1
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create chunk {chunk_num}: {e}")
            continue
    
    print(f"✅ Successfully split PDF into {len(split_files)} chunks")
    print(f"📁 Output directory: {output_dir}")
    
    # Show file sizes
    print("\n📊 Chunk sizes:")
    for file_path in split_files:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        filename = os.path.basename(file_path)
        print(f"   {filename}: {size_mb:.1f} MB")
    
    return split_files

def create_conversion_script(split_files, output_dir):
    """Create a script to convert all chunks"""
    script_path = os.path.join(output_dir, "convert_all_chunks.py")
    
    script_content = f'''#!/usr/bin/env python3
"""
Automated script to convert all PDF chunks using the document converter
"""
import os
import sys
import time
import requests
import json

# Add the project root to the path
sys.path.insert(0, '{os.path.abspath("/home/adebo/con")}')

def convert_chunk(file_path):
    """Convert a single PDF chunk"""
    print(f"🔄 Converting {{os.path.basename(file_path)}}...")
    
    try:
        # You can either:
        # 1. Use the Flask API (if running)
        # 2. Import and use the processor directly
        
        from processors.pdf_processor import PDFProcessor
        
        processor = PDFProcessor()
        
        def progress_callback(percentage, message):
            print(f"   {{percentage:3d}}% - {{message}}")
        
        processor.set_progress_callback(progress_callback)
        result = processor.process(file_path)
        
        if 'error' in result:
            print(f"❌ Error: {{result['error']}}")
            return False
        
        # Save result
        output_file = file_path.replace('.pdf', '_converted.md')
        with open(output_file, 'w', encoding='utf-8') as f:
            if isinstance(result, dict):
                f.write(processor.to_markdown(result))
            else:
                f.write(str(result))
        
        print(f"✅ Converted: {{os.path.basename(output_file)}}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to convert {{os.path.basename(file_path)}}: {{e}}")
        return False

def main():
    chunk_files = {split_files}
    
    print(f"🚀 Starting conversion of {{len(chunk_files)}} chunks...")
    
    successful = 0
    for chunk_file in chunk_files:
        if os.path.exists(chunk_file):
            if convert_chunk(chunk_file):
                successful += 1
            time.sleep(2)  # Small delay between conversions
        else:
            print(f"⚠️  Chunk file not found: {{chunk_file}}")
    
    print(f"\\n🎉 Conversion complete: {{successful}}/{{len(chunk_files)}} chunks converted successfully")

if __name__ == "__main__":
    main()
'''
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    print(f"📝 Created conversion script: {script_path}")
    return script_path

def main():
    parser = argparse.ArgumentParser(description='Split large PDFs for efficient OCR processing')
    parser.add_argument('input_pdf', help='Path to the input PDF file')
    parser.add_argument('-o', '--output', default=None, help='Output directory (default: input_filename_chunks)')
    parser.add_argument('-s', '--size', type=int, default=50, help='Pages per chunk (default: 50)')
    parser.add_argument('-p', '--prefix', default='chunk', help='Chunk filename prefix (default: chunk)')
    parser.add_argument('--create-script', action='store_true', help='Create conversion script for all chunks')
    
    args = parser.parse_args()
    
    # Check if pdftk is available
    if not check_pdftk():
        if not install_pdftk():
            sys.exit(1)
    
    # Set output directory
    if args.output is None:
        input_name = Path(args.input_pdf).stem
        args.output = f"{input_name}_chunks"
    
    # Get file size
    file_size_mb = os.path.getsize(args.input_pdf) / (1024 * 1024)
    print(f"📄 Input PDF: {args.input_pdf} ({file_size_mb:.1f} MB)")
    
    # Split the PDF
    split_files = split_pdf(args.input_pdf, args.output, args.size, args.prefix)
    
    if split_files and args.create_script:
        create_conversion_script(split_files, args.output)
        print(f"\\n🎯 To convert all chunks, run:")
        print(f"   cd {args.output} && python convert_all_chunks.py")

if __name__ == "__main__":
    main()
