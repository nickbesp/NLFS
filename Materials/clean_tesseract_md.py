"""Second-pass clean-up for the Tesseract-OCR'd books (output of run_ocr.py + clean_ocr_md.py).

Fixes what the first pass leaves behind:
- page markers "## Página N" (PDF page) -> "<!-- Página M -->" (printed page number;
  the offset is detected from the printed numbers OCR'd at the page edges);
- running headers/footers, which OCR garbles differently on every page, removed by
  fuzzy matching (words that recur at page edges on most pages);
- junk lines (spiral binding, decorations, stray letters);
- old-style numerals read as letters inside numbered lists ("4 Dónde; s Cuántos");
- articles/prepositions glued to the next word ("lasalida" -> "la salida");
- ALL-CAPS titles at the top of a page -> headings.

Usage:
    python clean_tesseract_md.py IN.md OUT.md --title "Book title" [--page-offset N] [--note "..."]
"""

import argparse
import collections
import re
import sys
import unicodedata
from pathlib import Path

from clean_ocr_md import Fixer, load_freq
from clean_vision_md import easyocr_fixes, fix_gender_slash, join_hyphenation  # '0' for 'o', URLs, n.º, ¿

sys.stdout.reconfigure(encoding="utf-8")

LETTER = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
WORD_RE = re.compile(rf"[{LETTER}]{{3,}}")
GLUED_RE = re.compile(r"\b(la|el|los|las|un|una|en|de|del|al|lo|se|me|te|su|sus|mi|tu)([a-záéíóúñü]{3,})\b", re.I)
STOPWORDS = set("para como pero este esta esto sobre entre desde hasta cuando donde porque también tiene están tienen todo todos".split())
OLDSTYLE = {"s": "5", "e": "6", "a": "3", "g": "9", "z": "2", "o": "0", "b": "6"}


def split_pages(text: str):
    """Pages by PDF number: "## Página N" (run_ocr.py) or "<!-- Page NNN -->" (convert_pdf_vision_local.py)."""
    chunks = re.split(r"^(?:## Página (\d+)|<!-- Page (\d+) -->)\s*$", text, flags=re.M)
    head = chunks[0]
    pages = []
    for i in range(1, len(chunks), 3):
        n = chunks[i] or chunks[i + 1]
        pages.append((int(n), chunks[i + 2]))
    return head, pages


def content_lines(body: str) -> list[str]:
    return [l for l in body.split("\n") if l.strip()]


def detect_offset(pages) -> int:
    """Most common (PDF page - printed number) for numbers OCR'd at page edges."""
    offsets = collections.Counter()
    for n, body in pages:
        lines = content_lines(body)
        for l in lines[:2] + lines[-3:]:
            for tok in re.findall(r"(?:^|\s)(\d{1,3})(?=\s|$)", l)[:1] + re.findall(r"(\d{1,3})\s*$", l):
                offsets[n - int(tok)] += 1
    if offsets:
        off, c = offsets.most_common(1)[0]
        if c >= max(3, len(pages) * 0.25):
            return off
    return 0


def running_words(pages, min_share=0.4) -> set:
    """Words (lower-case) that appear in edge lines on many pages: footer/header text."""
    seen = collections.Counter()
    for _, body in pages:
        lines = content_lines(body)
        words = set()
        for l in lines[:2] + lines[-2:]:
            # distinctive words only: common words recur at page edges anyway
            words |= {w.lower() for w in WORD_RE.findall(l) if len(w) >= 4 and w.lower() not in STOPWORDS}
        seen.update(words)
    return {w for w, c in seen.items() if c >= len(pages) * min_share and len(pages) >= 5}


def _prefix(word: str) -> str:
    base = unicodedata.normalize("NFD", word.lower())
    return "".join(c for c in base if not unicodedata.combining(c))[:5]


_PREFIX_CACHE = {}


def _prefixes(freq: dict) -> set:
    if id(freq) not in _PREFIX_CACHE:
        _PREFIX_CACHE[id(freq)] = {_prefix(w) for w in freq if len(w) >= 5}
    return _PREFIX_CACHE[id(freq)]


def is_junk(line: str, fixer: Fixer) -> bool:
    s = line.strip()
    if not s:
        return False
    if re.fullmatch(r"\d{1,3}[.)]?", s):  # bare item / page numbers: decided elsewhere
        return False
    if len(s) <= 3:
        # keep a single capital (option label) or a real short word
        return not (re.fullmatch(r"[A-ZÁÉÍÓÚ][.)]?", s) or s.strip("¿?¡!.,").lower() in fixer.freq)
    letters = sum(c.isalpha() for c in s)
    if letters < 0.4 * len(s.replace(" ", "")) and not re.search(r"\d", s):
        return True
    # grammar tables split words into morphemes ("(usted) pid-ió durm-ió le-yó"):
    # short tokens, but real content
    if len(re.findall(rf"[{LETTER}]-[{LETTER}]", s)) >= 2:
        return False
    # lines of long clean words are text, even in another language (glossaries)
    words_only = re.findall(rf"[{LETTER}]+", s)
    if len(words_only) >= 3 and sum(map(len, words_only)) / len(words_only) >= 4.5 \
            and letters >= 0.85 * len(s.replace(" ", "")):
        return False
    # spiral binding / decoration read as letters: short tokens that are mostly not words
    # ("anq vy r uu d", "- U r u U", "EN A — E E o A NEE")
    tokens = re.findall(rf"[{LETTER}]+", s)
    if tokens and not re.search(r"\d", s):
        longer = [t for t in tokens if len(t) >= 2]
        known = sum(t.lower() in fixer.freq for t in longer) / len(longer) if longer else 0.0
        avg = sum(map(len, tokens)) / len(tokens)
        if known < 0.6 and avg < 2.6:
            return True
        # word-search grids and decorative rows: capitals that form almost no words
        # ("CENVIDIOSOOSOTI!IYAOA", "E e o ccOOO CCCO OCOOCOCCOUOCOOCOCOLO")
        upper = sum(c.isupper() for c in s) / max(1, letters)
        if (len(tokens) >= 2 or len(tokens[0]) >= 8) and upper > 0.6 and known < 0.3:
            # rare or unaccented capitals ("COMUNICATIVOS GRAMATICALES LEXICOS") still
            # start like real words; random grid letters don't
            wordlike = sum(_prefix(t) in _prefixes(fixer.freq) for t in longer if len(t) >= 5)
            if wordlike < 0.5 * max(1, sum(len(t) >= 5 for t in longer)):
                return True
    return fixer.is_noise(s)


def fix_oldstyle_numerals(line: str) -> str:
    """'4 Dónde; s Cuántos' -> '4 Dónde; 5 Cuántos': only when the letter continues the count."""
    out, last = [], None
    for tok in re.split(r"(\s+)", line):
        bare = tok.strip(";.,:")
        if re.fullmatch(r"\d{1,2}", bare):
            last = int(bare)
        elif bare in OLDSTYLE and last is not None and int(OLDSTYLE[bare]) == (last + 1) % 10:
            tok = tok.replace(bare, OLDSTYLE[bare] if last + 1 < 10 else str(last + 1))
            last += 1
        out.append(tok)
    return "".join(out)


def unglue(line: str, freq: dict) -> str:
    def repl(m):
        word, art, rest = m.group(0), m.group(1), m.group(2)
        if word.lower() in freq or rest.lower() not in freq or freq.get(rest.lower(), 0) < 50:
            return word
        return f"{art} {rest}"

    return GLUED_RE.sub(repl, line)


def is_caps_heading(line: str) -> bool:
    s = line.strip()
    letters = re.findall(rf"[{LETTER}]", s)
    if len(letters) < 5 or len(s) > 70:
        return False
    return sum(c.isupper() for c in letters) / len(letters) > 0.85


def clean_body(body: str, printed: int, fixer: Fixer, running: set, vision: bool = False) -> str:
    lines = body.split("\n")
    idx = [i for i, l in enumerate(lines) if l.strip()]
    edges = set(idx[:2] + idx[-3:])
    out = []
    first_content = True
    for i, l in enumerate(lines):
        s = l.strip()
        if not s:
            if out and out[-1]:
                out.append("")
            continue
        if i in edges:
            words = [w.lower() for w in WORD_RE.findall(s)]
            hits = sum(w in running for w in words)
            # only short lines made largely of running words: body text near the page
            # edge can mention the same words ("el vocabulario" in an introduction)
            if (len(s) <= 80 and hits and (hits >= 2 or hits == len(words)) and hits >= 0.3 * len(words)) \
                    or re.fullmatch(rf"\D{{0,3}}{printed}\D{{0,3}}", s) \
                    or re.fullmatch(rf"{printed}\s+[a-záéíóúñ ]{{4,40}}\W*|[a-záéíóúñ ]{{4,40}}\s+{printed}\W*", s):
                # page number, alone or spelled out ("126 ciento veintiséis")
                continue
        if is_junk(s, fixer):
            continue
        s = easyocr_fixes(s)
        if vision:
            # EasyOCR keeps line-end hyphens inline ("adep- tos") and reads "o/a" as "ola";
            # Tesseract text was already de-hyphenated, and its inline hyphens are notation
            s = fix_gender_slash(join_hyphenation(s, fixer.freq), fixer.freq)
        s = fixer.fix_line(fix_oldstyle_numerals(unglue(s, fixer.freq)))
        if first_content and is_caps_heading(s):
            s = "## " + re.sub(r"^[^A-ZÁÉÍÓÚÑ¿¡]{1,6}", "", s).strip()
            out += ["", s, ""]
        else:
            out.append(s)
        first_content = False
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--title", required=True)
    ap.add_argument("--page-offset", type=int, default=None)
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    raw = unicodedata.normalize("NFC", Path(args.input).read_text(encoding="utf-8"))
    _, pages = split_pages(raw)
    vision = bool(re.search(r"^<!-- Page \d+ -->", raw, flags=re.M))  # EasyOCR input
    offset = detect_offset(pages) if args.page_offset is None else args.page_offset
    running = running_words(pages)
    fixer = Fixer(load_freq())

    parts = [f"# {args.title}\n"]
    if args.note:
        parts.append("\n".join(f"> {l}" for l in args.note.splitlines()) + "\n")
    for n, body in pages:
        printed = n - offset
        md = clean_body(body, printed, fixer, running, vision)
        marker = f"<!-- Página {printed} -->" if printed >= 1 else f"<!-- Portada (PDF {n}) -->"
        parts.append(f"{marker}\n\n{md}\n" if md else f"{marker}\n")
    Path(args.output).write_text("\n".join(parts), encoding="utf-8")
    print(f"Pages: {len(pages)} | offset {offset} | running words: {sorted(running)} | accent fixes: {sum(fixer.changes.values())}")


if __name__ == "__main__":
    main()
