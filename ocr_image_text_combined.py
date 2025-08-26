
import os
from pdf2image import convert_from_path
import pytesseract
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import white
from PIL import Image

# === CONFIGURATION ===
INPUT_FOLDER = "input_pdfs"
OUTPUT_FOLDER = "output_pdfs"

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Process each PDF in the input folder
for filename in os.listdir(INPUT_FOLDER):
    if filename.lower().endswith(".pdf"):
        input_path = os.path.join(INPUT_FOLDER, filename)
        output_path = os.path.join(OUTPUT_FOLDER, f"ocr_image_text_{filename}")
        print(f"Processing: {filename}")

        try:
            # Convert PDF to images
            images = convert_from_path(input_path, dpi=300)

            # Create a new PDF
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter

            for img in images:
                img_width, img_height = img.size
                x_scale = width / img_width
                y_scale = height / img_height

                # Draw original image
                c.drawInlineImage(img, 0, 0, width=width, height=height)

                # OCR with position data
                ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

                for i in range(len(ocr_data['text'])):
                    word = ocr_data['text'][i]
                    if word.strip():
                        x = ocr_data['left'][i] * x_scale
                        y = height - (ocr_data['top'][i] * y_scale)
                        c.setFont("Helvetica", 6)
                        c.setFillColor(white)  # white text on white background (semi-invisible)
                        c.drawString(x, y, word.strip())

                c.showPage()

            c.save()
            print(f"✅ Saved: {output_path}")
        except Exception as e:
            print(f"❌ Failed to process {filename}: {e}")
