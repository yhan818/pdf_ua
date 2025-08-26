import pikepdf

with pikepdf.open("output_pdfs/ocr_compressed_sample.pdf", allow_overwriting_input=True) as pdf:
    print(pdf.root)  # Should return a Dictionary object
    pdf.root.MarkInfo = pikepdf.Dictionary(Marked=True)
    pdf.save("test_output.pdf")