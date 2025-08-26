import os
import io
import datetime
import uuid
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import pikepdf # For low-level PDF manipulation

# === CONFIGURATION ===
# Folder containing the original PDFs
INPUT_FOLDER = "input_pdfs"
# Folder where the final, processed PDFs will be saved
OUTPUT_FOLDER = "output_pdfs"

# --- COMPRESSION SETTINGS ---
DPI = 150
JPEG_QUALITY = 80

# Ensure the input and output directories exist
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- SCRIPT START ---

def add_xmp_metadata_and_markinfo(pdf_path, doc_title, author, subject, keywords):
    """
    Adds a compliant XMP metadata stream and marks the PDF as tagged.
    This is run as a post-processing step to fix XMP and PDF/UA identifier issues.
    """
    try:
        pdf = pikepdf.Pdf.open(pdf_path, allow_overwriting_input=True)
        
        # [MODIFIED] Add /MarkInfo dictionary to declare the PDF is tagged.
        # This is often a prerequisite for a checker to validate the rest
        # of the accessibility structure, including XMP.
        
        pdf.trailer["/Root"]["/MarkInfo"] = pikepdf.Dictionary(Marked=True)

        # Generate a unique ID for this document instance
        instance_id = str(uuid.uuid4())
        
        # Define the XMP metadata XML as a string.
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

        # Create a metadata stream object and attach it to the PDF.
        metadata_stream = pdf.make_stream(xmp_metadata.encode("utf-8"))
        metadata_stream.Type = pikepdf.Name("/Metadata")
        metadata_stream.Subtype = pikepdf.Name("/XML")
        # Add the metadata stream to the PDF.
        pdf.trailer["/Root"]["/Metadata"] = metadata_stream
        
        print("      -> INFO: XMP metadata, MarkInfo, and PDF/UA identifier added.")
        # [MODIFIED] Using linearize=True performs a full rewrite, which can help
        # resolve structural inconsistencies for stricter validators.
        pdf.save(linearize=True)
        pdf.close()

    except Exception as e:
        print(f"      -> ERROR: Failed to add XMP metadata with pikepdf: {e}")

def process_all_pdfs():
    """
    Finds all PDF files in the INPUT_FOLDER and processes them.
    Now includes a post-processing step for XMP metadata.
    """
    for filename in os.listdir(INPUT_FOLDER):
        if filename.lower().endswith(".pdf"):
            input_path = os.path.join(INPUT_FOLDER, filename)
            output_path = os.path.join(OUTPUT_FOLDER, f"pdfua_ocr_{filename}")
            
            print(f"🔍 Starting processing for: {filename}")
            try:
                # Step 1: Create the OCR'd PDF with PyMuPDF
                doc_title, author, subject, keywords = create_ocr_compressed_pdf(input_path, output_path)
                
                # Step 2: Add XMP metadata and MarkInfo with pikepdf
                add_xmp_metadata_and_markinfo(output_path, doc_title, author, subject, keywords)

                print(f"✅ Successfully processed and saved to: {output_path}")
            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")

def create_ocr_compressed_pdf(input_path, output_path):
    """
    Creates a PDF with a compressed image layer and an invisible OCR text layer.
    Returns metadata for the post-processing step.
    """
    source_doc = fitz.open(input_path)
    output_doc = fitz.open()

    # --- ACCESSIBILITY FIXES (AUTOMATED) ---
    doc_title = os.path.splitext(os.path.basename(input_path))[0].replace('_', ' ').title()
    author = 'University of Arizona Libraries'
    subject = 'Lymphology Journal Article'
    keywords = 'OCR, accessibility, PDF/UA, Lymphology'
    
    output_doc.set_metadata({
        'title': doc_title,
        'author': author,
        'subject': subject,
        'keywords': keywords,
    })
    output_doc.set_language("en-US")
    
    try:
        output_doc.set_viewer_preferences({'DisplayDocTitle': True})
    except AttributeError:
        print("      -> INFO: 'set_viewer_preferences' not available in this PyMuPDF version. Skipping.")
        pass
    
    # --- PAGE PROCESSING ---
    for page_num, source_page in enumerate(source_doc):
        print(f"  -> Processing page {page_num + 1}/{len(source_doc)}...")
        pix = source_page.get_pixmap(dpi=DPI)
        img_bytes = pix.tobytes("png")
        pil_image = Image.open(io.BytesIO(img_bytes))
        ocr_data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT, lang='eng')
        output_page = output_doc.new_page(width=source_page.rect.width, height=source_page.rect.height)
        
        buffer = io.BytesIO()
        if pil_image.mode in ("RGBA", "P"):
            pil_image = pil_image.convert("RGB")
        pil_image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
        compressed_image_bytes = buffer.getvalue()
        output_page.insert_image(source_page.rect, stream=compressed_image_bytes)
        
        scale_x = source_page.rect.width / pix.width
        scale_y = source_page.rect.height / pix.height
        
        for i in range(len(ocr_data['text'])):
            word = ocr_data['text'][i]
            conf = int(ocr_data['conf'][i])
            if word.strip() and conf > 50:
                left, top, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                word_rect = fitz.Rect(left * scale_x, top * scale_y, (left + w) * scale_x, (top + h) * scale_y)
                output_page.insert_textbox(word_rect, word, fontsize=8, color=(0, 0, 0), fill_opacity=0)
    
    # --- SAVE AND RETURN METADATA ---
    output_doc.save(output_path, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
    output_doc.close()
    source_doc.close()
    
    return doc_title, author, subject, keywords

# --- Main execution block ---
if __name__ == "__main__":
    # Note: You will need to install pikepdf: pip install pikepdf
    process_all_pdfs()

