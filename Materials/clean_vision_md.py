"""Clean up a combined EasyOCR book produced by convert_pdf_vision_local.py.

Reuses the accent / ¿¡ / noise-line fixes from clean_ocr_md.py and adds fixes for
errors typical of EasyOCR (0 for "o", broken URLs, n.º). Page markers
"<!-- Page NNN -->" (PDF pages) become "<!-- Página N -->" (printed book pages).

Usage:
    python clean_vision_md.py INPUT.md OUTPUT.md --title "Book title" [--page-offset 1]
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

from clean_ocr_md import Fixer, clean_page, load_freq

sys.stdout.reconfigure(encoding="utf-8")

LETTER = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"

EASYOCR_FIXES = [
    # Spanish "o" (or) read as zero: "pasaporte 0 carné", "0 cualquier"
    # (but keep real ranges such as "de 0 a 5")
    (re.compile(rf"(?<=[{LETTER},)]) 0 (?=[{LETTER}])(?!a \d)"), " o "),
    (re.compile(rf"(?<=[{LETTER}]) 0,"), " o,"),
    # http:// read as http:Il, http:ll, http:/l ...
    (re.compile(r"\b(https?):\s*[/Il1|]{1,2}\s*"), r"\1://"),
    # www.domain with the dot dropped
    (re.compile(r"\bwww(?=[a-z0-9])"), "www."),
    # n.º / N.º variants: n. 1, n." 2, N:' 1, N.' 3
    (re.compile(r"\b([nN])[.:]\s*[\"'°º]?\s*(?=\d)"), r"\1.º "),
    # space before punctuation
    (re.compile(r"\s+([,.;:!?)])(?=\s|$)"), r"\1"),
    # "( MCER )" -> "(MCER)"
    (re.compile(r"\(\s+"), "("),
    # opening ¿ read as ":", "{", "«", "¢", ";" or "i" right before a question
    # (":qué tal?", "{cómo va todo?", "iQué hay?") - only when the line goes on to a "?"
    (re.compile(rf"(^|(?<=[\s(\-—]))[:{{«¢;]\s?(?=[{LETTER}][^?\n]{{0,80}}\?)"), "¿"),
    (re.compile(rf"(^|(?<=[\s(\-—]))i(?=[A-ZÁÉÍÓÚ][^?\s]*[^?\n]{{0,80}}\?)"), "¿"),
]


def easyocr_fixes(text: str) -> str:
    for pattern, repl in EASYOCR_FIXES:
        text = pattern.sub(repl, text)
    return text


FOOTER_RE = re.compile(r"^\s*Preparaci[oó]n\s+(al\s+)?Diploma de Espa[ñn]ol\s*\(Nivel\s*[B8]2\)\s*$", re.I)


def _norm(line: str) -> str:
    return re.sub(r"[^A-ZÁÉÍÓÚÑ]", "", line.upper())


def strip_running_lines(pages: list[str]) -> list[str]:
    """Drop the book's footer and repeat headers.

    A running header (section name such as "Comprensión de lectura") is kept on the
    first page where it appears and dropped while it repeats on following pages.
    """
    out, prev_heads = [], set()
    for body in pages:
        lines = [l for l in body.split("\n") if not FOOTER_RE.match(l.lstrip("# "))]
        content = [i for i, l in enumerate(lines) if l.strip()]
        heads = {_norm(lines[i].lstrip("# ")) for i in content[:3]} - {""}
        lines = [
            l for i, l in enumerate(lines)
            if not (i in content[:3] and _norm(l.lstrip("# ")) in prev_heads)
        ]
        prev_heads = heads
        out.append("\n".join(lines))
    return out


HYPHEN_RE = re.compile(r"\b([a-záéíóúüñ]+)\s?-\s+([a-záéíóúüñ]+)\b")


def join_hyphenation(text: str, freq: dict) -> str:
    """'adep- tos' / 'sustan - tivo' -> 'adeptos' / 'sustantivo' (line-end splits, joined by OCR)."""

    def repl(m):
        a, b = m.group(1), m.group(2)
        # join when the result is a word, or when neither half is one ("sustan- tivo");
        # a stem followed by a real word is grammar notation ("tendr- / hacer")
        if (a + b) in freq or (a not in freq and (b not in freq or len(b) <= 3)):
            return a + b
        return m.group(0)

    return HYPHEN_RE.sub(repl, text)


GENDER_RE = re.compile(rf"\b([{LETTER}]+)o(l|/)a\b")


def fix_gender_slash(text: str, freq: dict) -> str:
    """'Suegrola' / 'animadola' -> 'Suegro/a' / 'animado/a' (the slash is read as 'l').

    Only when the glued form is not a real word but the masculine stem is,
    so 'sola', 'hola', 'cola' stay untouched.
    """

    def repl(m):
        word, stem = m.group(0), m.group(1)
        if m.group(2) == "/":
            return word
        if word.lower() in freq or (stem + "o").lower() not in freq:
            return word
        return f"{stem}o/a"

    return GENDER_RE.sub(repl, text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--title", required=True)
    ap.add_argument("--page-offset", type=int, default=1, help="PDF page minus printed page number")
    args = ap.parse_args()

    raw = unicodedata.normalize("NFC", Path(args.input).read_text(encoding="utf-8"))
    chunks = re.split(r"^<!-- Page (\d+) -->\s*$", raw, flags=re.M)

    fixer = Fixer(load_freq())
    parts = [f"# {args.title}\n"]
    dropped = 0
    nums = chunks[1::2]
    bodies = strip_running_lines([re.sub(r"<!-- empty OCR page \d+ -->", "", b) for b in chunks[2::2]])
    for num, body in zip(nums, bodies):
        body = join_hyphenation(fix_gender_slash(easyocr_fixes(body), fixer.freq), fixer.freq)
        body, d = clean_page(body, fixer)
        dropped += d
        printed = int(num) - args.page_offset
        marker = f"<!-- Página {printed} -->" if printed >= 1 else f"<!-- Cubierta (PDF {int(num)}) -->"
        parts.append(f"{marker}\n\n{body}\n" if body else f"{marker}\n")

    Path(args.output).write_text("\n".join(parts), encoding="utf-8")
    print(f"Pages: {len(chunks) // 2} | accent fixes: {sum(fixer.changes.values())} | noise lines dropped: {dropped}")
    for (a, b), n in fixer.changes.most_common(25):
        print(f"  {n:4d}  {a} -> {b}")


if __name__ == "__main__":
    main()
