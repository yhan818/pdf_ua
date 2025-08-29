
# ==============================================================================
# PDF OCR, Compression, and PDF/UA Accessibility Helper Script
# ==============================================================================
#
# DESCRIPTION:
# This script processes PDF files to make them PDF/UA compliant. (not 100% yet)
# from an input folder by performing the following actions:
#   1. Renders each page as a compressed JPEG image to reduce file size.
#   2. Performs Optical Character Recognition (OCR) on the image to extract text.
#   3. Creates a new PDF with the compressed image and an invisible text layer on top.
#   4. Sets basic document metadata (Title, Author, Language).
#   5. Adds a compliant XMP metadata stream and a PDF/UA identifier to improve
#      accessibility and standards compliance.
#   6. More to do to fix the rest of PDF/UA compliance issues.
#   7. This script is a work in progress and will be updated as needed.
#   8. This script is not perfect and may not work for all PDFs. (random manual reveiws needed at the stage)
#   
# LIBRARIES REQUIRED:
# - PyMuPDF (fitz): pip install PyMuPDF
# - Pillow (PIL): pip install Pillow
# - pytesseract: pip install pytesseract
# - pikepdf: pip install pikepdf
# - Tesseract OCR Engine: Must be installed on your system.
#  Author: Yan Han with help from Gemini 2.5 Pro and GPT-4o
#  Date: 2025-08-26
#  Version: 1.0
#  License: MIT
#  Contact: yhan@arizona.edu
#  Website: https://github.com/yhan818/pdf_ua/
#  Description: This script processes PDF files to make them PDF/UA compliant.
# ==============================================================================

import os
import io
import datetime
import uuid
from PIL import Image
import pytesseract
import fitz      # PyMuPDF, used for core PDF reading and creation
import pikepdf   # Used for low-level PDF manipulation, like adding XMP metadata

# === CONFIGURATION ===
# Folder containing the original, unprocessed PDF files.
INPUT_FOLDER = "input_pdfs"
# Folder where the final, processed PDFs will be saved.
OUTPUT_FOLDER = "output_pdfs"

# --- COMPRESSION SETTINGS ---
# Dots Per Inch: Resolution for rendering PDF pages into images for OCR.
# Higher values improve OCR accuracy but increase processing time and file size.
DPI = 150
# Quality of the compressed JPEG images (1-100). Lower values mean smaller
# file sizes but lower image quality.
JPEG_QUALITY = 80

# --- SCRIPT SETUP ---
# Ensure the input and output directories exist before starting.
# If they don't exist, this will create them.
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ==============================================================================
# FUNCTION DEFINITIONS
# ==============================================================================

def add_xmp_metadata_and_markinfo(pdf_path, doc_title, author, subject, keywords):
    """
    Adds a compliant XMP metadata stream and marks the PDF as tagged.

    This function is run as a post-processing step after the main OCR PDF is
    created. It uses the `pikepdf` library to perform low-level modifications
    that are crucial for PDF/UA (Universal Accessibility) compliance.

    Args:
        pdf_path (str): The file path to the PDF to modify.
        doc_title (str): The document title.
        author (str): The document author.
        subject (str): The document subject/description.
        keywords (str): Comma-separated keywords.
    """
    try:
        # Open the PDF with pikepdf, allowing it to save changes to the same file.
        pdf = pikepdf.Pdf.open(pdf_path, allow_overwriting_input=True)

        # Add the /MarkInfo dictionary to the PDF's root. This dictionary explicitly
        # declares that the document contains tagged content, which is a fundamental
        # requirement for PDF accessibility checkers.
        pdf.trailer["/Root"]["/MarkInfo"] = pikepdf.Dictionary(Marked=True)

        # Generate a unique ID for this specific version of the document.
        instance_id = str(uuid.uuid4())

        # Define the XMP metadata XML as a multi-line f-string.
        # This structure provides machine-readable metadata that screen readers
        # and other assistive technologies can use. It includes standard fields
        # like title and creator, as well as the PDF/UA identifier.
        xmp_metadata = f'''
        <?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
        <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="pikepdf">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description rdf:about=""
                xmlns:dc="http://purl.org/dc/elements/1.1/"
                xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
                xmlns:pdfuaid="http://www.aiim.org/pdfua/ns/id/"
                xmlns:xmp="http://ns.adobe.com/xap/1.0/"
                xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/">
              <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{doc_title}</rdf:li></rdf:Alt></dc:title>
              <dc:creator><rdf:Seq><rdf:li>{author}</rdf:li></rdf:Seq></dc:creator>
              <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{subject}</rdf:li></rdf:Alt></dc:description>
              <dc:subject><rdf:Bag><rdf:li>{keywords.replace(",", "</rdf:li><rdf:li>")}</rdf:li></rdf:Bag></dc:subject>
              <pdf:Producer>pikepdf</pdf:Producer>
              <pdf:Keywords>{keywords}</pdf:Keywords>
              <xmp:CreateDate>{datetime.datetime.now(datetime.timezone.utc).isoformat()}</xmp:CreateDate>
              <xmp:CreatorTool>UA Libraries OCR and Accessibility Script</xmp:CreatorTool>
              <xmpMM:DocumentID>uuid:{instance_id}</xmpMM:DocumentID>
              <xmpMM:InstanceID>uuid:{instance_id}</xmpMM:InstanceID>
              <pdfuaid:part>1</pdfuaid:part>
            </rdf:Description>
          </rdf:RDF>
        </x:xmpmeta>
        <?xpacket end="w"?>
        '''

        # Create a metadata stream object from the XML string.
        metadata_stream = pdf.make_stream(xmp_metadata.encode("utf-8"))
        metadata_stream.Type = pikepdf.Name("/Metadata")
        metadata_stream.Subtype = pikepdf.Name("/XML")

        # Attach the metadata stream to the root of the PDF document.
        pdf.trailer["/Root"]["/Metadata"] = metadata_stream

        print("      -> INFO: XMP metadata, MarkInfo, and PDF/UA identifier added.")

        # Save the PDF. Using `linearize=True` (also known as "Fast Web View")
        # performs a full rewrite of the PDF. This helps resolve structural
        # inconsistencies and creates a cleaner file for stricter validators.
        pdf.save(linearize=True)
        pdf.close()

    except Exception as e:
        print(f"      -> ERROR: Failed to add XMP metadata with pikepdf: {e}")


def process_all_pdfs():
    """
    Finds all PDF files in the INPUT_FOLDER and its subdirectories, 
    processes them, and saves them to the OUTPUT_FOLDER with the same
    directory structure and filename.
    """
    for root, dirs, files in os.walk(INPUT_FOLDER):
        for filename in files:
            if filename.lower().endswith(".pdf"):
                input_path = os.path.join(root, filename)
                
                # Determine the relative path to maintain the directory structure
                relative_path = os.path.relpath(root, INPUT_FOLDER)
                output_dir = os.path.join(OUTPUT_FOLDER, relative_path)
                
                # Create the subdirectory in the output folder if it doesn't exist
                os.makedirs(output_dir, exist_ok=True)
                
                # The output path will have the same filename in the new structure
                output_path = os.path.join(output_dir, filename)

                print(f"🔍 Starting processing for: {input_path}")
                try:
                    doc_title, author, subject, keywords = create_ocr_compressed_pdf(input_path, output_path)
                    add_xmp_metadata_and_markinfo(output_path, doc_title, author, subject, keywords)
                    print(f"✅ Successfully processed and saved to: {output_path}")
                except Exception as e:
                    print(f"❌ Error processing {filename}: {e}")







def create_ocr_compressed_pdf(input_path, output_path):
    """
    Creates a new PDF with a compressed image layer and an invisible OCR text layer.

    This function handles the core OCR and compression logic. It returns the
    metadata used so it can be passed to the next processing step.

    Args:
        input_path (str): The file path of the source PDF.
        output_path (str): The file path where the new PDF will be saved.

    Returns:
        tuple: A tuple containing the doc_title, author, subject, and keywords.
    """
    # Open the original PDF document.
    source_doc = fitz.open(input_path)
    # Create a new, empty PDF document in memory for the output.
    output_doc = fitz.open()

    # --- SET DOCUMENT-LEVEL METADATA AND ACCESSIBILITY PROPERTIES ---
    # Automatically generate a title from the filename.
    doc_title = os.path.splitext(os.path.basename(input_path))[0].replace('_', ' ').title()
    author = 'University of Arizona Libraries'
    subject = 'Lymphology Journal Article'
    keywords = 'OCR, accessibility, PDF/UA, Lymphology'

    # Set the standard document metadata properties.
    output_doc.set_metadata({
        'title': doc_title,
        'author': author,
        'subject': subject,
        'keywords': keywords,
    })
    # Set the document's primary language, which is important for screen readers.
    output_doc.set_language("en-US")

    try:
        # This setting tells PDF viewers to display the document's title in the
        # window bar instead of the filename.
        output_doc.set_viewer_preferences({'DisplayDocTitle': True})
    except AttributeError:
        # Handle cases where the installed PyMuPDF version is older and lacks this method.
        print("      -> INFO: 'set_viewer_preferences' not available in this PyMuPDF version. Skipping.")
        pass

    # --- PROCESS EACH PAGE ---
    # Loop through every page in the source document.
    for page_num, source_page in enumerate(source_doc):
        print(f"  -> Processing page {page_num + 1}/{len(source_doc)}...")

        # Render the current page as a pixel map (image) at the specified DPI.
        pix = source_page.get_pixmap(dpi=DPI)
        # Convert the pixel map to raw PNG bytes.
        img_bytes = pix.tobytes("png")

        # Use Pillow to open the image from the raw bytes.
        pil_image = Image.open(io.BytesIO(img_bytes))

        # Perform OCR on the image using Tesseract to get structured data (words, positions).
        ocr_data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT, lang='eng')

        # Create a new blank page in the output document with the same dimensions as the original.
        output_page = output_doc.new_page(width=source_page.rect.width, height=source_page.rect.height)

        # --- COMPRESS AND INSERT THE BACKGROUND IMAGE ---
        # Create an in-memory buffer to hold the compressed image.
        buffer = io.BytesIO()
        # Ensure the image is in RGB format before saving as JPEG.
        if pil_image.mode in ("RGBA", "P"):
            pil_image = pil_image.convert("RGB")
        # Save the image to the buffer as a JPEG with the specified quality.
        pil_image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
        compressed_image_bytes = buffer.getvalue()
        # Insert the compressed JPEG as the background of the new page.
        output_page.insert_image(source_page.rect, stream=compressed_image_bytes)

        # --- INSERT THE INVISIBLE OCR TEXT LAYER ---
        # Calculate scaling factors to map OCR pixel coordinates back to PDF point coordinates.
        scale_x = source_page.rect.width / pix.width
        scale_y = source_page.rect.height / pix.height

        # Iterate through each word detected by the OCR process.
        for i in range(len(ocr_data['text'])):
            word = ocr_data['text'][i]
            conf = int(ocr_data['conf'][i]) # OCR confidence score (0-100).

            # Only process words that are not empty and have a confidence score above 50.
            if word.strip() and conf > 50:
                # Get the bounding box of the word in pixel coordinates.
                left, top, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                # Scale the bounding box to the PDF's coordinate system.
                word_rect = fitz.Rect(left * scale_x, top * scale_y, (left + w) * scale_x, (top + h) * scale_y)
                # Insert the word into a textbox at the calculated position.
                # `fill_opacity=0` makes the text layer invisible, so it can be selected
                # and read by screen readers without being visually distracting.
                output_page.insert_textbox(word_rect, word, fontsize=8, color=(0, 0, 0), fill_opacity=0)

    # --- SAVE THE FINAL PDF ---
    # Save the completed output document to a file.
    # garbage=4: Cleans up unused objects in the PDF to reduce file size.
    # deflate=True: Compresses the PDF's content streams.
    output_doc.save(output_path, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
    output_doc.close()
    source_doc.close()

    # Return the metadata so it can be used in the post-processing step.
    return doc_title, author, subject, keywords

# ==============================================================================
# SCRIPT EXECUTION
# ==============================================================================

# This block ensures the script's main function runs only when the file is
# executed directly (not when imported as a module).
if __name__ == "__main__":
    process_all_pdfs()
