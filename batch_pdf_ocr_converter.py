
import os
from pdf2image import convert_from_path
import pytesseract
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# === CONFIGURATION ===
INPUT_FOLDER = "input_pdfs"
OUTPUT_FOLDER = "output_pdfs"

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Process each PDF in the input folder
for filename in os.listdir(INPUT_FOLDER):
    if filename.lower().endswith(".pdf"):
        input_path = os.path.join(INPUT_FOLDER, filename)
        output_path = os.path.join(OUTPUT_FOLDER, f"ocr_{filename}")
        print(f"Processing: {filename}")

        try:
            # Convert PDF to images
            images = convert_from_path(input_path, dpi=300)

            # Create a new PDF with OCR text
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter

            for img in images:
                text = pytesseract.image_to_string(img)
                c.setFont("Helvetica", 10)
                y = height - 40
                for line in text.split('\n'):
                    if y < 40:
                        c.showPage()
                        c.setFont("Helvetica", 10)
                        y = height - 40
                    c.drawString(40, y, line.strip())
                    y -= 12
                c.showPage()

            c.save()
            print(f"✅ Saved: {output_path}")
        except Exception as e:
            print(f"❌ Failed to process {filename}: {e}")
