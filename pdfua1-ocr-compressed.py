import os
import io
from PIL import Image
import pytesseract
import fitz  # PyMuPDF

# === CONFIGURATION ===
# Folder containing the original PDFs
INPUT_FOLDER = "input_pdfs"
# Folder where the final, processed PDFs will be saved
OUTPUT_FOLDER = "output_pdfs"

# --- COMPRESSION SETTINGS ---
# DPI (Dots Per Inch) for rendering the PDF pages as images.
# Lowering this will reduce file size but may decrease OCR accuracy.
# 300 is high quality, 200 is a good balance, 150 is lower quality.
DPI = 150
# JPEG quality for the compressed images (1-95).
# Lower values create smaller files but result in more image artifacts.
# 80-85 is a good starting point.
JPEG_QUALITY = 80


# Ensure the input and output directories exist
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- SCRIPT START ---

def process_all_pdfs():
    """
    Finds all PDF files in the INPUT_FOLDER and processes them.
    """
    # Iterate over each file in the specified input folder
    for filename in os.listdir(INPUT_FOLDER):
        # Check if the file is a PDF, ignoring case
        if filename.lower().endswith(".pdf"):
            input_path = os.path.join(INPUT_FOLDER, filename)
            # Define the path for the final output file
            output_path = os.path.join(OUTPUT_FOLDER, f"ocr_compressed_{filename}")
            
            print(f"🔍 Starting processing for: {filename}")
            try:
                # Call the main function to perform OCR and compression
                create_ocr_compressed_pdf(input_path, output_path)
                print(f"✅ Successfully processed and saved to: {output_path}")
            except Exception as e:
                # Catch and report any errors during processing
                print(f"❌ Error processing {filename}: {e}")

def create_ocr_compressed_pdf(input_path, output_path):
    """
    Creates a new PDF with a compressed image layer and an invisible,
    searchable OCR text layer, and applies basic accessibility fixes.

    This script now automatically:
    1. Sets essential document metadata (Title, Author, etc.).
    2. Sets the document language to English.
    3. Sets the PDF to display the Document Title in the window bar.
    4. Removes any password-based encryption that would block screen readers.
    """
    # Open the original PDF document
    source_doc = fitz.open(input_path)
    # Create a new, empty PDF document for the output
    output_doc = fitz.open()

    # --- ACCESSIBILITY FIXES (AUTOMATED) ---

    # 1. Set Document Metadata (Title, Author, etc.)
    # This addresses the "Metadata stream does not contain dc:title" issue.
    # The title is crucial for screen readers to announce the document's purpose.
    doc_title = os.path.splitext(os.path.basename(input_path))[0].replace('_', ' ').title()
    output_doc.set_metadata({
        'title': doc_title,
        'author': 'University of Arizona Libraries',
        'subject': 'Lymphology Journal Article',
        'keywords': 'OCR, accessibility, PDF/UA, Lymphology',
    })

    # 2. Set Document Language
    # This addresses the "Natural language for document metadata undefined" issue.
    output_doc.set_language("en-US")

    # 3. Set Viewer Preferences to Display Document Title
    # This fixes the "DisplayDocTitle entry missing or false" issue.
    try:
        # This method works for modern versions of PyMuPDF (1.18.7+)
        output_doc.set_viewer_preferences({'DisplayDocTitle': True})
    except AttributeError:
        # This is a fallback for older versions of PyMuPDF that lack this method.
        # The script will continue without crashing.
        print("      -> INFO: 'set_viewer_preferences' not available in this PyMuPDF version. Skipping.")
        pass
    
    # --- PAGE PROCESSING (OCR AND COMPRESSION) ---

    # Process each page of the source document
    for page_num, source_page in enumerate(source_doc):
        print(f"  -> Processing page {page_num + 1}/{len(source_doc)}...")

        # 1. RENDER PAGE AS IMAGE
        pix = source_page.get_pixmap(dpi=DPI)
        
        # Convert the pixmap to a PIL Image object for Tesseract
        img_bytes = pix.tobytes("png")
        pil_image = Image.open(io.BytesIO(img_bytes))

        # 2. PERFORM OCR
        ocr_data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT, lang='eng')
        
        # 3. CREATE NEW PDF PAGE
        output_page = output_doc.new_page(width=source_page.rect.width, height=source_page.rect.height)

        # 4. ADD COMPRESSED IMAGE LAYER
        buffer = io.BytesIO()
        if pil_image.mode in ("RGBA", "P"):
            pil_image = pil_image.convert("RGB")
        pil_image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
        compressed_image_bytes = buffer.getvalue()
        output_page.insert_image(source_page.rect, stream=compressed_image_bytes)

        # 5. ADD INVISIBLE TEXT LAYER
        scale_x = source_page.rect.width / pix.width
        scale_y = source_page.rect.height / pix.height

        for i in range(len(ocr_data['text'])):
            word = ocr_data['text'][i]
            conf = int(ocr_data['conf'][i])

            if word.strip() and conf > 50:
                left, top, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                word_rect = fitz.Rect(left * scale_x, top * scale_y, (left + w) * scale_x, (top + h) * scale_y)
                
                output_page.insert_textbox(
                    word_rect,
                    word,
                    fontsize=8,
                    color=(0, 0, 0),
                    fill_opacity=0
                )
    
    # 6. SAVE FINAL PDF
    # The `encryption=0` parameter ensures the file is not encrypted,
    # fixing "Encrypted PDF disallows content extraction" issues.
    output_doc.save(output_path, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
    output_doc.close()
    source_doc.close()

# --- Main execution block ---
if __name__ == "__main__":
    # Note: This script requires Tesseract OCR engine to be installed on your system.
    # e.g., pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    process_all_pdfs()

