"""Batch OCR the scanned DELE B2 books with ocrmypdf, then convert to Markdown."""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path("C:/Users/topni/Учеба/Projects_Workshop/Nikita_Learn_Fucking_Spanish/Materials/DeLe_B2")
OUT = BASE / "ocr_output"
OUT.mkdir(exist_ok=True)

env = dict(os.environ)
env["PATH"] = env["PATH"] + os.pathsep + r"C:\Program Files\Tesseract-OCR"
env["TESSDATA_PREFIX"] = os.path.join(env["LOCALAPPDATA"], "tessdata")

# Order: most valuable first. Matched by filename prefix (names contain decomposed accents).
PREFIXES = [
    ("", "Grama"),
    ("", "Prepara"),
    ("", "Viva"),
    ("El_Libro", "Vocabulario-activo"),
    ("El_Libro", "Aula_2"),
    ("El_Libro", "Aula_4"),
]


def find(sub, prefix):
    return next(p for p in (BASE / sub).glob("*.pdf") if p.name.startswith(prefix))


def sidecar_to_md(txt: Path, title: str) -> str:
    # ocrmypdf separates pages in the sidecar with form feeds.
    pages = txt.read_text(encoding="utf-8").split("\f")
    parts = [f"# {title}\n"]
    for i, page in enumerate(pages, 1):
        if page.strip():
            parts.append(f"## Página {i}\n\n{page.strip()}\n")
    return "\n".join(parts)


def main():
    for sub, prefix in PREFIXES:
        src = find(sub, prefix)
        dst = OUT / src.name
        txt = dst.with_suffix(".txt")
        mdf = dst.with_suffix(".md")
        if mdf.exists() and mdf.stat().st_size > 0:
            print(f"SKIP (done): {src.name}", flush=True)
            continue
        print(f"OCR: {src.name}", flush=True)
        t = time.time()
        r = subprocess.run(
            [sys.executable, "-m", "ocrmypdf", "-l", "spa+eng", "--force-ocr",
             "--rotate-pages", "--deskew", "--jobs", "8", "--output-type", "pdf",
             "--sidecar", str(txt), str(src), str(dst)],
            env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            print(f"  FAILED (exit {r.returncode}):\n{r.stderr[-2000:]}", flush=True)
            continue
        print(f"  OCR done in {(time.time() - t) / 60:.1f} min", flush=True)
        try:
            mdf.write_text(sidecar_to_md(txt, src.stem), encoding="utf-8")
            print(f"  Markdown: {mdf.stat().st_size // 1024} KB", flush=True)
        except Exception as e:
            print(f"  Markdown FAILED: {e}", flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
