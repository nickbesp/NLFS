"""Faithful PDF -> Markdown for PDFs that have a real text layer (no OCR, no LLM).

Extracts each page's text with pdfium and only removes extraction artifacts; the
text itself is never rewritten, so nothing is summarised or invented.

Structure comes from how the page is printed:
- headings: lines set larger than the body text (glyph height per line), with
  levels taken from the document's own size hierarchy; for PDFs without one,
  an ALL-CAPS line at the top of a page;
- bold body-size lines become **labels**;
- lines repeated at the top/bottom of most pages (running headers, footers,
  page numbers) are removed, and "<!-- Página N -->" markers are added.

Usage:
    python convert_pdf_text_md.py BOOK.pdf OUT.md --title "Book title"
        [--page-offset 0] [--headings auto|size|caps] [--note "..."]
"""

import argparse
import collections
import ctypes
import re
import sys
import unicodedata
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

sys.stdout.reconfigure(encoding="utf-8")

# Private-use bullet glyphs from Symbol/Wingdings fonts, and common bullets.
BULLET_CHARS = "•●▪■‣⁃"
BULLET_RE = re.compile(rf"^\s*[{BULLET_CHARS}]\s*")
INVISIBLE_RE = re.compile("[￾­​﻿\u0002]")  # soft hyphens, zero-width, BOM, STX
BLANK_RE = re.compile(r"(?:_\s?){3,}|_{3,}")  # "_ _ _ _" / "______" answer blanks
DOTS_RE = re.compile(r"(?:…|\.){4,}|…{2,}")  # dot leaders
LETTER = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
CONNECTORS = "DE|DEL|EN|LA|LAS|LOS|EL|Y|E|O|CON|A|AL|PARA|POR|SU|SUS"


# ---------------------------------------------------------------- extraction

def extract_lines(page) -> list[dict]:
    """Lines of a page with their dominant glyph height and font weight."""
    tp = page.get_textpage()
    n = pdfium_c.FPDFText_CountChars(tp.raw)
    rect = pdfium_c.FS_RECTF()
    lines, text, heights, weights = [], [], [], []

    def flush():
        line = unicodedata.normalize("NFC", INVISIBLE_RE.sub("", "".join(text))).rstrip()
        h = collections.Counter(heights).most_common(1)[0][0] if heights else 0.0
        w = collections.Counter(weights).most_common(1)[0][0] if weights else 400
        lines.append({"text": line, "h": h, "w": w})
        text.clear(), heights.clear(), weights.clear()

    for k in range(n):
        ch = chr(pdfium_c.FPDFText_GetUnicode(tp.raw, k))
        if ch == "\x00":
            ch = "□"  # glyph without a Unicode mapping: the PDF itself shows a box
        elif ch == "\t":
            ch = " "
        if ch == "\n":
            flush()
            continue
        if ch == "\r":
            continue
        text.append(ch)
        if ch.strip():
            # the loose box follows the rendered size; the nominal font size can be 1.0
            # when text is scaled through the drawing matrix
            pdfium_c.FPDFText_GetLooseCharBox(tp.raw, k, ctypes.byref(rect))
            heights.append(round((rect.top - rect.bottom) * 2) / 2)
            weights.append(pdfium_c.FPDFText_GetFontWeight(tp.raw, k))
    flush()
    tp.close()
    return lines


def _key(text: str) -> str:
    return re.sub(r"\d+", "#", text.strip().lower())


def _edges(lines: list[dict]) -> list[int]:
    idx = [i for i, l in enumerate(lines) if l["text"].strip()]
    return sorted(set(idx[:3] + idx[-3:]))


def detect_page_offset(pages: list[list[dict]]):
    """Most common (PDF page - printed number) among bare numbers at page edges, or None."""
    offsets = collections.Counter()
    for p, lines in enumerate(pages, start=1):
        for i in _edges(lines):
            t = lines[i]["text"].strip()
            if re.fullmatch(r"\d{1,4}", t):
                offsets[p - int(t)] += 1
    if offsets:
        off, count = offsets.most_common(1)[0]
        if count >= max(3, len(pages) * 0.3):
            return off
    return None


def strip_running_lines(pages: list[list[dict]], page_offset, min_share: float = 0.4) -> None:
    """Remove running headers/footers and printed page numbers (in place).

    A bare number is only removed when it is this page's own number: workbooks put
    numbers at page edges as content too (e.g. "write these numbers in words").
    """
    edge_keys = collections.Counter()
    for lines in pages:
        edge_keys.update({_key(lines[i]["text"]) for i in _edges(lines)})
    running = {
        k for k, c in edge_keys.items()
        if len(pages) >= 5 and c >= len(pages) * min_share and not re.fullmatch(r"#", k)
    }
    for p, lines in enumerate(pages, start=1):
        for i in _edges(lines):
            t = lines[i]["text"].strip()
            if re.fullmatch(r"\d{1,4}", t):
                if page_offset is not None and int(t) == p - page_offset:
                    lines[i]["text"] = ""
            elif _key(t) in running:
                lines[i]["text"] = ""


# ---------------------------------------------------------------- structure

def is_caps_heading(line: str) -> bool:
    s = line.strip()
    letters = re.findall(rf"[{LETTER}]", s)
    if len(letters) < 4 or len(s) > 70 or "____" in s or "…" in s or DOTS_RE.search(s):
        return False
    return sum(c.isupper() for c in letters) / len(letters) > 0.9 and len(s.split()) <= 10


def size_levels(pages: list[list[dict]]) -> tuple[float, dict]:
    """Body glyph height and {height: '##'/'###'/'####'} for larger heading sizes."""
    by_height = collections.Counter()
    for lines in pages:
        for l in lines:
            by_height[l["h"]] += len(l["text"].strip())
    if not by_height:
        return 0.0, {}
    body = by_height.most_common(1)[0][0]
    candidates = collections.Counter()
    for lines in pages:
        for l in lines:
            t = l["text"].strip()
            if l["h"] >= body * 1.15 and 2 <= len(t) <= 100 and re.search(rf"[{LETTER}]{{2}}", t):
                candidates[l["h"]] += 1
    # keep sizes that recur (a one-off huge glyph is decoration, e.g. a cover)
    sizes = sorted((h for h, c in candidates.items() if c >= 2), reverse=True)[:3]
    return body, {h: "#" * (i + 2) for i, h in enumerate(sizes)}


def tidy(line: str) -> str:
    line = BULLET_RE.sub("- ", line)
    line = BLANK_RE.sub("____ ", line)
    line = DOTS_RE.sub(" … ", line)
    return re.sub(r"[ \t]{2,}", " ", line).strip()


def page_markdown(lines: list[dict], mode: str, body: float, levels: dict) -> str:
    out: list[str] = []
    seen = 0
    last_kind = None  # heading level / "bold" of the previous source line, for re-joining wraps
    for l in lines:
        line = tidy(l["text"])
        if not line:
            if out and out[-1] != "":
                out.append("")
            last_kind = None
            continue
        seen += 1

        kind = None
        if mode == "size":
            if l["h"] in levels and len(line) <= 100:
                kind = levels[l["h"]]
            elif l["w"] >= 550 and abs(l["h"] - body) <= 1 and len(line) <= 60:
                # a label starts like one and doesn't continue a sentence (italic fonts
                # can report a heavy weight for wrapped translations)
                last = next((x for x in reversed(out) if x), "")
                starts = re.match(r"[A-ZÁÉÍÓÚÑ0-9¿¡]", line)
                after_break = not last or last.startswith(("#", "**")) or re.search(r"[.:;?!)]$", last)
                if (starts and (after_break or last_kind == "bold")) or (last_kind == "bold" and line[0].islower()):
                    kind = "bold"
        elif seen == 1 and is_caps_heading(line):
            kind = "##"

        if kind:
            prev_idx = next((i for i in range(len(out) - 1, -1, -1) if out[i]), None)
            # labels are often stacked ("Tarea 1" / "Formato de la tarea:"), so a bold
            # line only continues the previous one when it starts in lower case
            wrapped = kind != "bold" or line[0].islower()
            if kind == last_kind and prev_idx is not None and wrapped:
                # a heading / label wrapped onto the next line
                if kind == "bold":
                    out[prev_idx] = out[prev_idx][:-2] + " " + line + "**"
                else:
                    out[prev_idx] += " " + line
            elif kind == "bold":
                out.append(f"**{line}**")
            else:
                out += ["", f"{kind} {line}", ""]
            last_kind = kind
            continue
        if last_kind == "bold" and out and out[-1].startswith("**"):
            # label/value tables: the label's last word shares a line with the value
            # ("**Extensión de los**" + "textos: Entre 400 y 450 palabras.")
            m = re.match(r"([a-záéíóúñ]+(?: [a-záéíóúñ]+)?:)\s*(.*)", line)
            if m:
                out[-1] = out[-1][:-2] + " " + m.group(1) + "**" + (" " + m.group(2) if m.group(2) else "")
                last_kind = None
                continue
        last_kind = None

        prev = next((x for x in reversed(out) if x), "")
        if mode == "caps" and prev.startswith("#"):
            idx = len(out) - 1 - out[::-1].index(prev)
            # ALL-CAPS title broken mid-phrase: "... INDICATIVO (se" + "caracteriza ...",
            # "... SER, ESTAR," + "TENER"; a line starting with an article or a single
            # letter is content ("A B C", "EL SALÓN")
            if line[0].islower() and re.search(r"\b[a-záéíóúñ]+$", prev):
                out[idx] = prev + " " + line
                continue
            if seen == 2 and is_caps_heading(line) and (
                re.search(rf",$|\b({CONNECTORS})$", prev) or re.match(r"(DE|DEL|EN|CON|PARA|POR)\b", line)
            ):
                out[idx] = prev + " " + line
                continue

        prev = out[-1] if out else ""
        # sentence wrapped across lines: no closing punctuation, next starts in lower case
        if (prev and not prev.startswith(("#", "- ", "**")) and line[0].islower()
                and not re.search(r"[.:;?!)»\]]$", prev) and "____" not in prev):
            out[-1] = prev + " " + line
        # word hyphenated across lines: "inte-" + "gración"
        elif prev.endswith("-") and line[0].islower() and re.search(rf"[{LETTER}]-$", prev):
            out[-1] = prev[:-1] + line
        else:
            out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("output")
    ap.add_argument("--title", required=True)
    ap.add_argument("--page-offset", type=int, default=None,
                    help="PDF page minus printed page number (default: detected from printed page numbers)")
    ap.add_argument("--headings", choices=["auto", "size", "caps"], default="auto")
    ap.add_argument("--note", default="", help="Text for a '>' note under the title")
    ap.add_argument("--fill-from", default=None,
                    help="Folder with page_NNN.md (OCR, by PDF page number) used for pages without a text layer")
    args = ap.parse_args()

    pdf = pdfium.PdfDocument(args.pdf)
    pages = [extract_lines(pdf[i]) for i in range(len(pdf))]
    pdf.close()
    detected = detect_page_offset(pages)
    if args.page_offset is None:
        args.page_offset = detected if detected is not None else 0
    strip_running_lines(pages, args.page_offset)

    body, levels = size_levels(pages)
    n_size_headings = sum(1 for lines in pages for l in lines if l["h"] in levels and l["text"].strip())
    mode = args.headings
    if mode == "auto":
        # use the size hierarchy when it exists and marks a sane share of lines
        total = sum(1 for lines in pages for l in lines if l["text"].strip())
        mode = "size" if levels and 3 <= n_size_headings <= total * 0.15 else "caps"

    parts = [f"# {args.title}\n"]
    if args.note:
        parts.append("\n".join(f"> {l}" for l in args.note.splitlines()) + "\n")
    empty, filled = [], []
    for i, lines in enumerate(pages):
        printed = i + 1 - args.page_offset
        body_md = page_markdown(lines, mode, body, levels)
        ocr_file = Path(args.fill_from or "", f"page_{i + 1:03d}.md")
        if not body_md and args.fill_from and ocr_file.exists():
            # image-only page inside a text PDF: use OCR, with the EasyOCR clean-up fixes
            from clean_vision_md import easyocr_fixes, join_hyphenation
            from clean_ocr_md import load_freq

            freq = load_freq()
            ocr = join_hyphenation(easyocr_fixes(ocr_file.read_text(encoding="utf-8")), freq).strip()
            # capital I read for lower-case l: "Ilevar", "Ileva" -> "llevar", "lleva"
            ocr = re.sub(
                r"\bI(l[a-záéíóúüñ]+)",
                lambda m: "l" + m.group(1) if ("l" + m.group(1)).lower() in freq and ("I" + m.group(1)).lower() not in freq
                else m.group(0),
                ocr,
            )
            if ocr:
                body_md = "<!-- OCR: this page has no text layer -->\n\n" + ocr
                filled.append(i + 1)
        marker = f"<!-- Página {printed} -->" if printed >= 1 else f"<!-- Portada (PDF {i + 1}) -->"
        parts.append(f"{marker}\n\n{body_md}\n" if body_md else f"{marker}\n")
        if not body_md:
            empty.append(i + 1)
    Path(args.output).write_text("\n".join(parts), encoding="utf-8")
    print(f"Pages: {len(pages)} | page offset {args.page_offset} (detected {detected}) | headings: {mode} (body {body}, levels {levels}) | empty: {empty or 'none'} | filled by OCR: {filled or 'none'}")


if __name__ == "__main__":
    main()
