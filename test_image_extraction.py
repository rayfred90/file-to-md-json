#!/usr/bin/env python3
"""
Test script for PDF image extraction functionality with MinIO folder-based storage
Tests the enhanced PDF processor with image extraction and saves to MinIO document folders
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from processors.pdf_processor import PDFProcessor
from minio_storage.minio_service import MinIOService


def test_pdf_image_extraction_with_minio(pdf_path: str):
    """
    Test PDF image extraction functionality with MinIO folder-based storage
    
    Args:
        pdf_path: Path to the PDF file to test
    """
    print("🧪 PDF Image Extraction Test with MinIO Storage")
    print("=" * 60)
    
    # Validate PDF file
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found: {pdf_path}")
        return False
    
    print(f"📄 Testing PDF: {pdf_path}")
    print(f"📁 File size: {os.path.getsize(pdf_path):,} bytes")
    print()
    
    try:
        # Initialize services
        print("🔧 Initializing services...")
        processor = PDFProcessor()
        minio_service = MinIOService()
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        print("🔄 Processing PDF and extracting images...")
        
        # Process PDF with image extraction (processor expects file path)
        result = processor.process(pdf_path)
        
        if not result.get('text') and result.get('error'):
            print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
            return False, None
        
        # Display processing results
        print("✅ PDF processing completed successfully!")
        print()
        
        # Text content summary
        text_content = result.get('text', '')
        print(f"📝 Extracted text: {len(text_content):,} characters")
        if text_content:
            preview = text_content[:200].replace('\n', ' ')
            print(f"   Preview: {preview}...")
        print()
        
        # Image extraction results
        images = result.get('images', [])
        print(f"🖼️  Extracted images: {len(images)} found")
        
        if images:
            print("\n📋 Image Details:")
            print("-" * 40)
            
            total_size = 0
            for i, img in enumerate(images, 1):
                size_kb = len(img['base64_data']) * 3 / 4 / 1024  # Approximate size from base64
                total_size += size_kb
                
                print(f"  {i:2d}. {img['filename']}")
                print(f"      Page: {img['page_num']}")
                print(f"      Size: {img['width']}x{img['height']} ({size_kb:.1f} KB)")
                print(f"      Format: {img['format']}")
                print()
            
            print(f"📊 Total images size: {total_size:.1f} KB")
        else:
            print("   No images found in the PDF")
        
        # Test MinIO folder-based storage
        print("\n🗂️  Testing MinIO Folder-Based Storage:")
        print("-" * 40)
        
        # Create document folder
        document_name = os.path.basename(pdf_path)
        session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"📁 Creating document folder for: {document_name}")
        document_id = minio_service.create_document_folder(document_name, session_id)
        print(f"   Document ID: {document_id}")
        
        # Upload original PDF
        print(f"📤 Uploading original PDF...")
        success, original_path = minio_service.upload_to_document_folder(
            document_id, pdf_content, document_name, 'original'
        )
        if success:
            print(f"   ✅ Original uploaded: {original_path}")
        else:
            print(f"   ❌ Failed to upload original PDF")
        
        # Save converted markdown
        markdown_content = processor.to_markdown(result)
        markdown_filename = f"{os.path.splitext(document_name)[0]}.md"
        print(f"📤 Uploading converted markdown...")
        success, converted_path = minio_service.upload_to_document_folder(
            document_id, markdown_content.encode('utf-8'), markdown_filename, 'converted'
        )
        if success:
            print(f"   ✅ Markdown uploaded: {converted_path}")
        else:
            print(f"   ❌ Failed to upload markdown")
        
        # Save extracted images
        if images:
            print(f"📤 Uploading {len(images)} extracted images...")
            saved_paths = minio_service.save_images_to_document_folder(document_id, images)
            print(f"   ✅ Images uploaded: {len(saved_paths)}/{len(images)} successful")
            
            for path in saved_paths[:3]:  # Show first 3 paths
                print(f"      - {path}")
            if len(saved_paths) > 3:
                print(f"      ... and {len(saved_paths) - 3} more")
        
        # Display folder metadata
        print(f"\n📋 Document Folder Metadata:")
        print("-" * 40)
        metadata = minio_service.get_document_metadata(document_id)
        if metadata:
            print(f"   Document ID: {metadata['document_id']}")
            print(f"   Document Name: {metadata['document_name']}")
            print(f"   Session ID: {metadata['session_id']}")
            print(f"   Created: {metadata['created_at']}")
            print(f"   Files:")
            files = metadata.get('files', {})
            for file_type, file_data in files.items():
                if file_type == 'original' and file_data:
                    print(f"      {file_type}: {file_data['name']}")
                elif isinstance(file_data, list) and file_data:
                    print(f"      {file_type}: {len(file_data)} files")
        
        # Test folder listing
        print(f"\n📂 Testing Document Folder Listing:")
        print("-" * 40)
        folders = minio_service.list_document_folders(session_id)
        print(f"   Found {len(folders)} folders for session: {session_id}")
        
        # Generate markdown output sample
        print("\n📄 Markdown Output Sample:")
        print("-" * 40)
        markdown_preview = markdown_content[:500]
        print(markdown_preview)
        if len(markdown_content) > 500:
            print("...")
        
        print(f"\n✅ Test completed successfully!")
        print(f"   Document ID: {document_id}")
        print(f"   Text: {len(text_content):,} chars")
        print(f"   Images: {len(images)} extracted")
        print(f"   Markdown: {len(markdown_content):,} chars")
        print(f"   MinIO Storage: ✅ Folder-based organization working")
        
        return True, document_id
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_local_image_extraction(pdf_path: str, output_dir: str = None):
    """
    Test PDF image extraction functionality (local-only version for comparison)
    
    Args:
        pdf_path: Path to the PDF file to test
        output_dir: Directory to save extracted images (optional)
    """
    print("🧪 PDF Image Extraction Test (Local)")
    print("=" * 50)
    
    # Validate PDF file
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found: {pdf_path}")
        return False
    
    print(f"📄 Testing PDF: {pdf_path}")
    print(f"📁 File size: {os.path.getsize(pdf_path):,} bytes")
    print()
    
    try:
        # Initialize PDF processor
        processor = PDFProcessor()
        
        print("🔄 Processing PDF and extracting images...")
        
        # Process PDF with image extraction (processor expects file path)
        result = processor.process(pdf_path)
        
        if not result.get('text') and result.get('error'):
            print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Display results
        print("✅ PDF processing completed successfully!")
        print()
        
        # Text content summary
        text_content = result.get('text', '')
        print(f"📝 Extracted text: {len(text_content):,} characters")
        if text_content:
            preview = text_content[:200].replace('\n', ' ')
            print(f"   Preview: {preview}...")
        print()
        
        # Image extraction results
        images = result.get('images', [])
        print(f"🖼️  Extracted images: {len(images)} found")
        
        if images:
            print("\n📋 Image Details:")
            print("-" * 40)
            
            total_size = 0
            for i, img in enumerate(images, 1):
                size_kb = len(img['base64_data']) * 3 / 4 / 1024  # Approximate size from base64
                total_size += size_kb
                
                print(f"  {i:2d}. {img['filename']}")
                print(f"      Page: {img['page_num']}")
                print(f"      Size: {img['width']}x{img['height']} ({size_kb:.1f} KB)")
                print(f"      Format: {img['format']}")
                print()
            
            print(f"📊 Total images size: {total_size:.1f} KB")
            
            # Save images if output directory provided
            if output_dir:
                save_extracted_images(images, output_dir)
            
        else:
            print("   No images found in the PDF")
        
        # Generate markdown output sample
        print("\n📄 Markdown Output Sample:")
        print("-" * 40)
        markdown_content = processor.to_markdown(result)
        
        # Show first 500 characters of markdown
        markdown_preview = markdown_content[:500]
        print(markdown_preview)
        if len(markdown_content) > 500:
            print("...")
        
        print(f"\n✅ Test completed successfully!")
        print(f"   Text: {len(text_content):,} chars")
        print(f"   Images: {len(images)} extracted")
        print(f"   Markdown: {len(markdown_content):,} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_extracted_images(images: list, output_dir: str):
    """
    Save extracted images to local directory for testing
    
    Args:
        images: List of image dictionaries with base64 data
        output_dir: Directory to save images
    """
    import base64
    
    print(f"\n💾 Saving images to: {output_dir}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    saved_count = 0
    for img in images:
        try:
            # Decode base64 image data
            img_data = base64.b64decode(img['base64_data'])
            
            # Create filename
            filename = img['filename']
            output_path = os.path.join(output_dir, filename)
            
            # Save image file
            with open(output_path, 'wb') as f:
                f.write(img_data)
            
            print(f"   ✅ Saved: {filename}")
            saved_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to save {img.get('filename', 'unknown')}: {e}")
    
    print(f"\n📁 Saved {saved_count}/{len(images)} images to {output_dir}")


def main():
    """Main test function"""
    # Default test PDF
    test_pdf = "sample.pdf"
    
    # Check for command line argument
    if len(sys.argv) > 1:
        test_pdf = sys.argv[1]
    
    # Check for test mode
    test_mode = "minio"  # Default to MinIO test
    if len(sys.argv) > 2 and sys.argv[2] == "local":
        test_mode = "local"
    
    print(f"🎯 Running test mode: {test_mode.upper()}")
    print()
    
    if test_mode == "minio":
        # Run MinIO-based test
        success, document_id = test_pdf_image_extraction_with_minio(test_pdf)
        
        if success:
            print(f"\n🎉 MinIO test passed!")
            print(f"   Document folder created: {document_id}")
            sys.exit(0)
        else:
            print(f"\n💥 MinIO test failed!")
            sys.exit(1)
    else:
        # Run local test
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"test_images_{timestamp}"
        
        success = test_local_image_extraction(test_pdf, output_dir)
        
        if success:
            print(f"\n🎉 Local test passed!")
            sys.exit(0)
        else:
            print(f"\n💥 Local test failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()
