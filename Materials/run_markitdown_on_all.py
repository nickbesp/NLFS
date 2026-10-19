import os
import glob
import sys
import traceback
from pathlib import Path
from markitdown import MarkItDown

# Reconfigure stdout to use UTF-8 to prevent Windows terminal encoding errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    # Setup markitdown
    print("Initializing MarkItDown...")
    try:
        md = MarkItDown()
    except Exception as e:
        print(f"Failed to initialize MarkItDown: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Search for all PDF files in the current folder and subfolders
    base_dir = Path("C:/Users/topni/Учеба/Projects_Workshop/Nikita_Learn_Fucking_Spanish/Materials")
    pdf_files = list(base_dir.rglob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF file(s) to convert.")
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        md_path = pdf_path.with_suffix(".md")
        
        # Skip if already exists
        if md_path.exists():
            print(f"  -> Markdown file already exists at {md_path.name}. Skipping.")
            continue
            
        print("  Converting...")
        try:
            start_time = os.times()[4]
            result = md.convert(str(pdf_path))
            end_time = os.times()[4]
            
            # Save the result
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(result.text_content)
                
            duration = end_time - start_time
            print(f"  -> Successfully converted in {duration:.2f} seconds!")
            print(f"  -> Saved to: {md_path.name}")
            
        except Exception as e:
            print(f"  -> ERROR converting {pdf_path.name}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main()
