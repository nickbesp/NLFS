import os
import sys
import glob
import time
import argparse
from pathlib import Path
import pypdfium2 as pdfium
import google.generativeai as genai

# Setup Gemini API key
api_key = os.environ.get("GEMINI_API_KEY")

PROMPT = """
You are a professional document converter. Convert the following Spanish textbook page image into clean, structured Markdown (.md) format.
Follow these rules strictly:
1. Keep the exact text and meanings. Do not translate Spanish to English unless it is already side-by-side in the text.
2. Structure headers properly (e.g. #, ##, ###).
3. If there are tables, side-by-side word lists, or comparisons, represent them as clean Markdown tables.
4. If there are exercises, represent them as bullet points or numbered lists.
5. Preserve text decorations like bolding, italics, or highlights where they are important for grammar rules.
6. Do not include book header titles, page numbers, or footer copyright lines in the markdown.
7. Return only the markdown content, no extra talk or wrapper code blocks.
"""

def convert_pdf_file(pdf_path, start_page, end_page, output_dir):
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Please set it in your terminal before running this script.")
        print("Example (PowerShell): $env:GEMINI_API_KEY='your_api_key'")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    pdf_name = Path(pdf_path).name
    pdf_base = Path(pdf_path).stem
    pdf_output_dir = Path(output_dir) / pdf_base
    pdf_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n--- Starting conversion for: {pdf_name} ---")
    
    pdf = pdfium.PdfDocument(pdf_path)
    total_pages = len(pdf)
    
    start_idx = max(0, start_page - 1) if start_page else 0
    end_idx = min(total_pages, end_page) if end_page else total_pages
    
    print(f"Total pages in PDF: {total_pages}")
    print(f"Processing page range: {start_idx + 1} to {end_idx}")

    for page_idx in range(start_idx, end_idx):
        page_num = page_idx + 1
        md_file_path = pdf_output_dir / f"page_{page_num:03d}.md"
        
        # Resume capability: skip if page is already converted
        if md_file_path.exists():
            print(f"Page {page_num}/{end_idx} already exists. Skipping.")
            continue
            
        print(f"Converting Page {page_num}/{end_idx}...", end="", flush=True)
        
        try:
            # Render page to PIL image
            page = pdf[page_idx]
            page_image = page.render_topil(scale=2)  # Scale 2 is 144 DPI (great quality for OCR)
            
            # Call Gemini
            response = model.generate_content([PROMPT, page_image])
            markdown_content = response.text.strip()
            
            # Save page markdown
            with open(md_file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
                
            print(" Done.")
            time.sleep(1.5)  # Moderate sleep to prevent rate limits
            
        except Exception as e:
            print(f" Error processing page {page_num}: {e}")
            print("Waiting 10 seconds before continuing...")
            time.sleep(10)
            
    pdf.close()
    
    # Concatenate processed pages into a single file
    combined_md_name = f"{pdf_base}_pages_{start_idx+1}_{end_idx}.md" if (start_page or end_page) else f"{pdf_base}.md"
    combined_md_path = Path(pdf_path).parent / combined_md_name
    print(f"Combining pages into single file: {combined_md_path}...")
    
    page_files = sorted(pdf_output_dir.glob("page_*.md"))
    # Filter files within our range
    in_range_files = []
    for pf in page_files:
        try:
            num = int(pf.stem.split('_')[1])
            if (start_idx + 1) <= num <= end_idx:
                in_range_files.append(pf)
        except:
            pass
            
    with open(combined_md_path, "w", encoding="utf-8") as outfile:
        for page_file in in_range_files:
            page_title = f"\n\n<!-- Page {Path(page_file).stem.split('_')[1]} -->\n"
            outfile.write(page_title)
            with open(page_file, "r", encoding="utf-8") as infile:
                outfile.write(infile.read())
                
    print(f"Conversion complete! Output saved to {combined_md_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDF to Markdown page-by-page using Gemini.")
    parser.add_argument("pdf_file", help="Path to the PDF file")
    parser.add_argument("--start", type=int, default=None, help="Start page number (1-indexed)")
    parser.add_argument("--end", type=int, default=None, help="End page number (1-indexed)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_file):
        print(f"Error: File '{args.pdf_file}' does not exist.")
        sys.exit(1)
        
    cache_dir = os.path.join(os.path.dirname(args.pdf_file), "conversion_cache")
    convert_pdf_file(args.pdf_file, args.start, args.end, cache_dir)
