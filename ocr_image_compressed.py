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
    searchable OCR text layer.

    This version is more efficient because it:
    1. Uses PyMuPDF for all PDF operations, removing the need for reportlab.
    2. Processes images and text in memory, avoiding temporary files.
    3. Uses a reliable method for creating invisible text (fill_opacity=0).
    4. Compresses images using a configurable DPI and JPEG quality setting.
    """
    # Open the original PDF document
    source_doc = fitz.open(input_path)
    # Create a new, empty PDF document for the output
    output_doc = fitz.open()

    # Set metadata for the output PDF for PDF/UA compliance
    output_doc.set_metadata({
        "title": " Yan Han OCR Processed PDF, to be updated later",  # You can make this dynamic
        "author": "Yan Han, the University of Arizona Libraries",
        "subject": "Lymphology",
        "keywords": "OCR, accessibility, PDF/UA, Lymphology", # can add more keywords later
    })  # [ADDED]

    # Process each page of the source document
    for page_num, source_page in enumerate(source_doc):
        print(f"  -> Processing page {page_num + 1}/{len(source_doc)}...")

        # 1. RENDER PAGE AS IMAGE
        # Render the page to a pixmap using the configured DPI.
        pix = source_page.get_pixmap(dpi=DPI)
        
        # Convert the pixmap to a PIL Image object for Tesseract
        img_bytes = pix.tobytes("png")  # Use lossless PNG for OCR step
        pil_image = Image.open(io.BytesIO(img_bytes))

        # 2. PERFORM OCR
        # Use pytesseract to get detailed OCR data, including word positions
        ocr_data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
        
        # 3. CREATE NEW PDF PAGE
        # Create a new page in the output PDF with the same dimensions as the original
        output_page = output_doc.new_page(width=source_page.rect.width, height=source_page.rect.height)

        # 4. ADD COMPRESSED IMAGE LAYER
        # Save the PIL image (created for OCR) to a byte buffer 
        # with a specific JPEG quality for compression.
        buffer = io.BytesIO()
        # Convert to RGB if it has an alpha channel, as JPEG doesn't support it.
        if pil_image.mode in ("RGBA", "P"):
            pil_image = pil_image.convert("RGB")
        pil_image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
        compressed_image_bytes = buffer.getvalue()
        
        # Insert the compressed image, making it fill the entire page
        output_page.insert_image(source_page.rect, stream=compressed_image_bytes)


        # 5. ADD INVISIBLE TEXT LAYER
        # Calculate scaling factors to map OCR coordinates (from the rendered image)
        # back to the PDF's coordinate system (points).
        scale_x = source_page.rect.width / pix.width
        scale_y = source_page.rect.height / pix.height

        # Iterate through each detected word from OCR
        for i in range(len(ocr_data['text'])):
            word = ocr_data['text'][i]
            conf = int(ocr_data['conf'][i])

            # Process the word only if it's not empty and has a high confidence score
            if word.strip() and conf > 50:  # Confidence threshold (0-100)
                # Get the bounding box of the word from OCR data
                left, top, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                
                # Scale the bounding box to the PDF's coordinate system
                word_rect = fitz.Rect(left * scale_x, top * scale_y, 
                                      (left + w) * scale_x, (top + h) * scale_y)
                
                # Insert the text into the rectangle.
                # 'fill_opacity=0' makes the text fill invisible but still selectable/searchable.
                output_page.insert_textbox(
                    word_rect,
                    word,
                    fontsize=8,  # A small fontsize is fine as it's invisible
                    color=(0, 0, 0), # Text color doesn't matter, but we set it anyway
                    fill_opacity=0
                )
    
    # 6. SAVE FINAL PDF
    # Save the document with garbage collection to remove unused objects and deflation to compress.
    # This ensures the smallest possible file size.
    output_doc.save(output_path, garbage=4, deflate=True, encryption=0)
    output_doc.close()
    source_doc.close()

# --- Main execution block ---
if __name__ == "__main__":
    # Note: This script requires Tesseract OCR engine and Poppler to be installed on your system.
    # Ensure the pytesseract command is configured if Tesseract is not in your system's PATH.
    # e.g., pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    process_all_pdfs()

