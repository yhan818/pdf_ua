This project is intended to fix PDF files to make them PDF/UA compliant. (not 100% yet)

It has  an input folder by performing the following actions:
 1. Renders each page as a compressed JPEG image to reduce file size.
 2. Performs Optical Character Recognition (OCR) on the image to extract text.
 3. Creates a new PDF with the compressed image and an invisible text layer on top.
 4. Sets basic document metadata (Title, Author, Language).
 5. Adds a compliant XMP metadata stream and a PDF/UA identifier to improve accessibility and standards compliance.

There are More to do to fix the rest of PDF/UA compliance issues. It is a work in progress and will be updated as needed. This script is not perfect and may not work for all PDFs. (random manual reveiws needed at the stage)
