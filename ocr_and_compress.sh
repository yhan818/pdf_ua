
#!/bin/bash

# === CONFIGURATION ===
INPUT_FOLDER="input_pdfs"
OUTPUT_FOLDER="output_pdfs"
mkdir -p "$OUTPUT_FOLDER"

for file in "$INPUT_FOLDER"/*.pdf; do
    filename=$(basename -- "$file")
    base="${filename%.*}"
    echo "🔍 Processing $filename..."

    # Step 1: Run OCR (searchable text layer + PDF/A)
    ocrmypdf --output-type pdfa "$file" "$OUTPUT_FOLDER/${base}_ocr.pdf"

    # Step 2: Compress using Ghostscript
    gs -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook -dNOPAUSE -dQUIET -dBATCH        -sOutputFile="$OUTPUT_FOLDER/${base}_ocr_compressed.pdf"        "$OUTPUT_FOLDER/${base}_ocr.pdf"

    echo "✅ Output saved: ${base}_ocr_compressed.pdf"
done
