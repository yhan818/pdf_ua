
import os
from pdf2image import convert_from_path
import pytesseract
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import white
from PIL import Image
import fitz  # PyMuPDF

# === CONFIGURATION ===
INPUT_FOLDER = "input_pdfs"
OUTPUT_FOLDER = "output_pdfs"
TEMP_FOLDER = "temp_images"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Step 1: Create OCR+Image PDF
for filename in os.listdir(INPUT_FOLDER):
    if filename.lower().endswith(".pdf"):
        input_path = os.path.join(INPUT_FOLDER, filename)
        raw_output_path = os.path.join(OUTPUT_FOLDER, f"raw_ocr_{filename}")
        final_output_path = os.path.join(OUTPUT_FOLDER, f"ocr_compressed_{filename}")
        print(f"🔍 Processing: {filename}")

        try:
            images = convert_from_path(input_path, dpi=300)
            c = canvas.Canvas(raw_output_path, pagesize=letter)
            width, height = letter

            for page_num, img in enumerate(images):
                img_width, img_height = img.size
                x_scale = width / img_width
                y_scale = height / img_height

                # Save temp image for later compression
                img_path = os.path.join(TEMP_FOLDER, f"page_{page_num}.png")
                img.save(img_path)

                # Draw image and overlay OCR text
                c.drawInlineImage(img, 0, 0, width=width, height=height)
                ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

                for i in range(len(ocr_data['text'])):
                    word = ocr_data['text'][i]
                    if word.strip():
                        x = ocr_data['left'][i] * x_scale
                        y = height - (ocr_data['top'][i] * y_scale)
                        c.setFont("Helvetica", 6)
                        c.setFillColor(white)
                        c.drawString(x, y, word.strip())

                c.showPage()

            c.save()
            print(f"✅ OCR+Image PDF saved: {raw_output_path}")

            # Step 2: Compress images in PDF using JPX
            doc = fitz.open(raw_output_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n > 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    temp_jpx = os.path.join(TEMP_FOLDER, f"img_{page_num}_{img_index}.jp2")
                    pix.write_image(temp_jpx, format="jp2")
                    page.insert_image(page.rect, filename=temp_jpx)
                    doc._deleteObject(xref)

            doc.save(final_output_path, deflate=True)
            print(f"🎉 Compressed PDF saved: {final_output_path}")

        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
