#!/usr/bin/env python3
"""
Create a sample PDF with embedded images for testing image extraction
"""

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    from PIL import Image, ImageDraw
    import datetime
    import io
    import os
    
    def create_sample_images():
        """Create simple test images"""
        images = []
        
        # Create a simple red rectangle image
        img1 = Image.new('RGB', (200, 100), color='red')
        draw1 = ImageDraw.Draw(img1)
        draw1.text((10, 40), "Test Image 1", fill='white')
        
        img1_bytes = io.BytesIO()
        img1.save(img1_bytes, format='PNG')
        img1_bytes.seek(0)
        images.append(('red_rect.png', img1_bytes))
        
        # Create a simple blue circle image
        img2 = Image.new('RGB', (150, 150), color='blue')
        draw2 = ImageDraw.Draw(img2)
        draw2.ellipse([25, 25, 125, 125], fill='yellow', outline='white', width=3)
        draw2.text((50, 70), "Image 2", fill='black')
        
        img2_bytes = io.BytesIO()
        img2.save(img2_bytes, format='PNG')
        img2_bytes.seek(0)
        images.append(('blue_circle.png', img2_bytes))
        
        # Create a simple green gradient image
        img3 = Image.new('RGB', (180, 120), color='green')
        draw3 = ImageDraw.Draw(img3)
        for i in range(60):
            shade = int(255 * (i / 60))
            draw3.rectangle([i*3, 20, i*3+2, 100], fill=(0, shade, 0))
        draw3.text((10, 10), "Gradient Image", fill='white')
        
        img3_bytes = io.BytesIO()
        img3.save(img3_bytes, format='PNG')
        img3_bytes.seek(0)
        images.append(('green_gradient.png', img3_bytes))
        
        return images
    
    def create_test_pdf_with_images(filename="test_pdf_with_images.pdf"):
        """Create a PDF with embedded images"""
        print("🖼️  Creating sample images...")
        images = create_sample_images()
        
        print(f"📄 Creating PDF with images: {filename}")
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        # Page 1 - Title and first image
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 80, "PDF with Embedded Images - Test Document")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 120, f"Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(100, height - 140, "Purpose: Testing PDF image extraction functionality")
        
        # Add first image
        c.drawString(100, height - 180, "Image 1 - Red Rectangle:")
        img1_reader = ImageReader(images[0][1])
        c.drawImage(img1_reader, 100, height - 300, width=200, height=100)
        
        # Add some text after image
        c.drawString(100, height - 340, "This is text content after the first image.")
        c.drawString(100, height - 360, "The PDF processor should extract both text and images.")
        
        # Page 2 - More images and content
        c.showPage()
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, height - 80, "Page 2 - Additional Images")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 120, "Image 2 - Blue Circle with Yellow Center:")
        
        # Reset image stream position
        images[1][1].seek(0)
        img2_reader = ImageReader(images[1][1])
        c.drawImage(img2_reader, 100, height - 280, width=150, height=150)
        
        c.drawString(320, height - 200, "Image 3 - Green Gradient:")
        
        # Reset image stream position
        images[2][1].seek(0)
        img3_reader = ImageReader(images[2][1])
        c.drawImage(img3_reader, 320, height - 280, width=180, height=120)
        
        # Add more text content
        c.drawString(100, height - 320, "Text content between images:")
        c.drawString(100, height - 340, "• This PDF contains multiple embedded images")
        c.drawString(100, height - 360, "• Images are in PNG format")
        c.drawString(100, height - 380, "• Text and images are mixed throughout the document")
        c.drawString(100, height - 400, "• This tests the complete image extraction pipeline")
        
        # Page 3 - Summary
        c.showPage()
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, height - 80, "Page 3 - Test Summary")
        
        c.setFont("Helvetica", 12)
        summary_content = [
            "Test Document Summary:",
            "",
            "• Total Pages: 3",
            "• Total Images: 3",
            "• Image Formats: PNG",
            "• Text Content: Mixed with images",
            "",
            "Expected Extraction Results:",
            "• Text: All paragraphs and lists",
            "• Images: 3 images extracted as JPEG (converted)",
            "• Metadata: PDF properties and image details",
            "",
            "This document should test the complete PDF processing",
            "pipeline including image extraction, text extraction,",
            "and MinIO folder-based storage organization."
        ]
        
        y_position = height - 120
        for line in summary_content:
            c.drawString(100, y_position, line)
            y_position -= 20
        
        # Save the PDF
        c.save()
        print(f"✅ Created test PDF with images: {filename}")
        print(f"📊 Document contains 3 pages and 3 embedded images")
        return filename
        
    if __name__ == "__main__":
        create_test_pdf_with_images()
        
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Installing required packages...")
    import subprocess
    try:
        subprocess.run(["pip", "install", "reportlab", "Pillow"], check=True)
        print("✅ Dependencies installed. Please run the script again.")
    except Exception as install_error:
        print(f"❌ Failed to install dependencies: {install_error}")
        print("Please install manually: pip install reportlab Pillow")
        
except Exception as e:
    print(f"❌ Failed to create PDF with images: {e}")
    import traceback
    traceback.print_exc()
