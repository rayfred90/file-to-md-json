#!/usr/bin/env python3
"""
Create a sample PDF for testing
"""

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    import datetime
    
    def create_test_pdf(filename="test_document.pdf"):
        # Create a new PDF
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        # Add title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, "Sample PDF Document for Testing")
        
        # Add some content
        c.setFont("Helvetica", 12)
        y_position = height - 150
        
        content = [
            "This is a sample PDF document created for testing the document converter.",
            "",
            "Document Details:",
            f"- Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "- Purpose: Testing PDF to Markdown conversion",
            "- Content: Multiple paragraphs and formatting examples",
            "",
            "Sample Content:",
            "",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod",
            "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim",
            "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea",
            "commodo consequat.",
            "",
            "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum",
            "dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non",
            "proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
            "",
            "Technical Information:",
            "- File format: PDF",
            "- Text encoding: UTF-8", 
            "- Pages: Multiple",
            "- Content type: Mixed text and formatting"
        ]
        
        for line in content:
            c.drawString(100, y_position, line)
            y_position -= 20
            
            # Start new page if needed
            if y_position < 100:
                c.showPage()
                c.setFont("Helvetica", 12)
                y_position = height - 100
        
        # Add a second page with more content
        c.showPage()
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, height - 100, "Page 2 - Additional Content")
        
        c.setFont("Helvetica", 12)
        y_position = height - 150
        
        more_content = [
            "This is the second page of the test document.",
            "",
            "Key Features to Test:",
            "• Multi-page document handling",
            "• Text extraction accuracy",
            "• Formatting preservation", 
            "• Performance with larger documents",
            "",
            "Sample Data Table:",
            "Name        | Age | Location",
            "------------|-----|----------",
            "John Doe    | 30  | New York",
            "Jane Smith  | 25  | London",
            "Bob Johnson | 35  | Tokyo",
            "",
            "End of test document.",
            "",
            "This PDF should be successfully converted to Markdown format",
            "with all text content preserved and properly structured."
        ]
        
        for line in more_content:
            c.drawString(100, y_position, line)
            y_position -= 20
        
        # Save the PDF
        c.save()
        print(f"✅ Created test PDF: {filename}")
        return filename
        
    if __name__ == "__main__":
        create_test_pdf()
        
except ImportError:
    print("❌ reportlab not installed. Installing...")
    import subprocess
    subprocess.run(["pip", "install", "reportlab"])
    
    # Try again
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import datetime
        
        def create_test_pdf(filename="test_document.pdf"):
            # Same code as above
            c = canvas.Canvas(filename, pagesize=letter)
            width, height = letter
            
            c.setFont("Helvetica-Bold", 16)
            c.drawString(100, height - 100, "Sample PDF Document for Testing")
            
            c.setFont("Helvetica", 12)
            y_position = height - 150
            
            content = [
                "This is a sample PDF document created for testing the document converter.",
                "",
                f"Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "Purpose: Testing PDF to Markdown conversion",
                "",
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "This document contains multiple lines of text to test",
                "the PDF processing capabilities of the converter.",
                "",
                "End of test document."
            ]
            
            for line in content:
                c.drawString(100, y_position, line)
                y_position -= 20
            
            c.save()
            print(f"✅ Created test PDF: {filename}")
            return filename
        
        if __name__ == "__main__":
            create_test_pdf()
            
    except Exception as e:
        print(f"❌ Failed to create PDF: {e}")
        print("Please provide your own PDF file for testing.")
