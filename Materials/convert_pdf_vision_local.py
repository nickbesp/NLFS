"""
Local vision PDF -> Markdown converter (no Gemini / cloud APIs).

Renders each page to an image, runs EasyOCR (es+en), reconstructs reading
order from bounding boxes into structured Markdown. Supports resume via
per-page cache files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def boxes_to_items(boxes, texts, confidences):
    """Turn EasyOCR (bbox, text, conf) results into flat box dicts."""
    items = []
    for box, text, conf in zip(boxes, texts, confidences):
        text = (text or "").strip()
        if not text:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        items.append(
            {
                "text": text,
                "conf": float(conf),
                "x0": x0,
                "x1": x1,
                "y0": y0,
                "y1": y1,
                "yc": (y0 + y1) / 2,
                "h": max(y1 - y0, 1.0),
            }
        )
    return items


def line_slope_samples(items):
    """(x, dy/dx) between horizontally adjacent boxes of the same text line.

    EasyOCR boxes are axis-aligned, so tilt (pages curving toward the spine) only
    shows up in how neighbouring boxes on one line step up or down.
    """
    samples = []
    by_x = sorted(items, key=lambda it: it["x0"])
    for i, a in enumerate(by_x):
        for b in by_x[i + 1:]:
            gap = b["x0"] - a["x1"]
            if gap > a["h"] * 2:
                break
            if gap < -a["h"] or abs(b["yc"] - a["yc"]) > min(a["h"], b["h"]) * 0.6:
                continue
            xa, xb = (a["x0"] + a["x1"]) / 2, (b["x0"] + b["x1"]) / 2
            if xb - xa > a["h"] * 2:
                samples.append(((xa + xb) / 2, (b["yc"] - a["yc"]) / (xb - xa)))
    return samples


def baseline_drift(items):
    """Function x -> vertical drift of the text baseline relative to the block's left edge.

    Fits the local slope as a linear function of x (lines bend more near the spine),
    trims outliers, and integrates it. Returns None for flat text.
    """
    samples = line_slope_samples(items)
    if len(samples) < 4:
        return None
    xs = np.array([x for x, _ in samples])
    ks = np.array([k for _, k in samples])
    x_ref = min(it["x0"] for it in items)
    keep = np.ones(len(ks), dtype=bool)
    coef = np.array([0.0, float(np.median(ks))])
    for _ in range(2):
        if keep.sum() >= 6 and np.ptp(xs[keep]) > 0:
            coef = np.polyfit(xs[keep] - x_ref, ks[keep], 1)
        else:
            coef = np.array([0.0, float(np.median(ks[keep]))])
        resid = ks - np.polyval(coef, xs - x_ref)
        mad = float(np.median(np.abs(resid))) or 1e-6
        keep = np.abs(resid) <= 3 * mad
    b_, a_ = coef  # slope(x) = a_ + b_ * (x - x_ref)
    width = max(it["x1"] for it in items) - x_ref
    if abs(a_) * width + abs(b_) * width**2 / 2 < 3:  # under 3 px drift across the block
        return None
    return lambda x: a_ * (x - x_ref) + b_ / 2 * (x - x_ref) ** 2


def estimate_line_pitch(items):
    """Median vertical distance from a box to the nearest box directly below it."""
    dys = []
    for a in items:
        best = None
        for b in items:
            dy = b["yc"] - a["yc"]
            if dy <= a["h"] * 0.3:
                continue
            overlap = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
            if overlap > 0.3 * min(a["x1"] - a["x0"], b["x1"] - b["x0"]) and (best is None or dy < best):
                best = dy
        if best is not None and best < a["h"] * 2.5:
            dys.append(best)
    return float(np.median(dys)) if len(dys) >= 5 else None


def group_items_to_lines(items, y_tol_ratio: float = 0.6):
    """Group boxes into lines by vertical proximity, then left-to-right."""
    if not items:
        return []

    # Pages curving toward the spine bend lines upward, so a line's right end can sit
    # level with the next line's start. Straighten the baselines before grouping.
    drift = baseline_drift(items)
    if drift:
        items = [dict(it, yc=it["yc"] - drift((it["x0"] + it["x1"]) / 2)) for it in items]

    # With tight leading, box heights (ascenders + descenders) exceed the line pitch,
    # so a height-based tolerance would merge neighbouring lines.
    pitch = estimate_line_pitch(items)
    items = sorted(items, key=lambda it: (it["yc"], it["x0"]))
    lines = []
    current = [items[0]]
    current_yc = items[0]["yc"]
    current_h = items[0]["h"]

    for it in items[1:]:
        tol = max(current_h, it["h"]) * y_tol_ratio
        if pitch:
            tol = min(tol, pitch * 0.45)
        if abs(it["yc"] - current_yc) <= tol:
            current.append(it)
            current_yc = (current_yc * (len(current) - 1) + it["yc"]) / len(current)
            current_h = max(current_h, it["h"])
        else:
            current.sort(key=lambda x: x["x0"])
            lines.append(current)
            current = [it]
            current_yc = it["yc"]
            current_h = it["h"]

    current.sort(key=lambda x: x["x0"])
    lines.append(current)
    return lines


def group_boxes_to_lines(boxes, texts, confidences, y_tol_ratio: float = 0.6):
    return group_items_to_lines(boxes_to_items(boxes, texts, confidences), y_tol_ratio)


def _find_gaps(items, lo_key, hi_key, min_gap):
    """Centres of empty runs along one axis that are at least min_gap wide."""
    spans = sorted((it[lo_key], it[hi_key]) for it in items)
    gaps = []
    reach = spans[0][1]
    for lo, hi in spans[1:]:
        if lo - reach >= min_gap:
            gaps.append((reach + lo) / 2)
        reach = max(reach, hi)
    return gaps


def _split(items, char_h: float, axis: str):
    """Split boxes at gutters (axis "x") or gaps (axis "y"); None if there is no valid cut."""
    if axis == "x":
        # Column gutters on scans are slightly slanted/ragged, so line ends poke into
        # them. Shrinking boxes horizontally before the search ignores small overhangs,
        # while a real full-width line still blocks the cut.
        shrink = char_h * 0.4
        probe = [dict(it, x0=it["x0"] + shrink, x1=max(it["x0"] + shrink, it["x1"] - shrink)) for it in items]
        cuts = _find_gaps(probe, "x0", "x1", char_h * 0.3)
    else:
        # Lines inside a paragraph overlap vertically (box heights include ascenders).
        cuts = _find_gaps(items, "y0", "y1", char_h * 0.5)
    if not cuts:
        return None
    groups = [[] for _ in range(len(cuts) + 1)]
    for it in items:
        c = (it["x0"] + it["x1"]) / 2 if axis == "x" else it["yc"]
        groups[sum(c > cut for cut in cuts)].append(it)
    groups = [g for g in groups if g]
    if len(groups) < 2:
        return None
    height = max(it["y1"] for it in items) - min(it["y0"] for it in items)
    if axis == "x" and height > char_h * 2:
        # Real columns run most of the block's height; a short gap that happens
        # to line up inside a paragraph does not.
        spans = [max(it["y1"] for it in g) - min(it["y0"] for it in g) for g in groups]
        if min(spans) < height * 0.5:
            return None
        # A narrow first column of item numbers ("23.", "24." ...) means an answer
        # table: it must be read row by row, not column by column.
        first = groups[0]
        width = max(it["x1"] for it in first) - min(it["x0"] for it in first)
        numbered = sum(bool(re.fullmatch(r"\d{1,2}\s*[.)]?", it["text"])) for it in first)
        if width < char_h * 3 and len(first) >= 3 and numbered >= len(first) * 0.6:
            return None
    return groups


def xy_cut(items, char_h: float, depth: int = 0):
    """Recursive XY-cut: split at column gutters first, then at vertical gaps.

    Returns blocks (lists of boxes) in reading order, so multi-column pages are
    read column by column instead of line-interleaved.
    """
    if len(items) <= 1 or depth > 12:
        return [items]

    for axis in ("x", "y"):
        groups = _split(items, char_h, axis)
        if groups:
            blocks = []
            for g in groups:
                blocks.extend(xy_cut(g, char_h, depth + 1))
            return blocks

    # A title or footer sitting tight against two columns blocks both cuts.
    # Peel off lines at the top or bottom and retry on the rest. Magazine articles
    # can have a title plus a 4-5 line lede across the columns, so allow up to 8.
    lines = group_items_to_lines(items)
    if len(lines) > 3:
        for k in range(1, min(8, len(lines) // 3) + 1):
            for head, rest_lines, tail in ((lines[:k], lines[k:], []), ([], lines[:-k], lines[-k:])):
                rest = [it for line in rest_lines for it in line]
                if _split(rest, char_h, "x"):
                    out = xy_cut([it for line in head for it in line], char_h, depth + 1) if head else []
                    out += xy_cut(rest, char_h, depth + 1)
                    if tail:
                        out += xy_cut([it for line in tail for it in line], char_h, depth + 1)
                    return out
    return [items]


def drop_edge_blocks(blocks, page_w: float, margin_ratio: float = 0.07):
    """Drop narrow blocks hugging the left/right edge (bleed-through of the facing page)."""
    kept = []
    for b in blocks:
        x0 = min(it["x0"] for it in b)
        x1 = max(it["x1"] for it in b)
        if x1 < page_w * margin_ratio or x0 > page_w * (1 - margin_ratio):
            continue
        kept.append(b)
    return kept


def line_text(line_items) -> str:
    return " ".join(it["text"] for it in line_items).strip()


def is_page_noise(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    # lone page numbers / chapter crumbs
    if re.fullmatch(r"\d{1,4}", t):
        return True
    if re.fullmatch(r"[ivxlcdmIVXLCDM]{1,6}", t):
        return True
    if len(t) <= 2 and not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]", t):
        return True
    return False


def looks_like_heading(text: str, mean_h: float, line_h: float) -> bool:
    if len(text) > 90:
        return False
    # Tall boxes alone are not enough: a garbage box spanning two lines is tall too.
    if line_h >= mean_h * 1.35 and 3 <= len(text) <= 45:
        return True
    # ALL CAPS short titles
    letters = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]", text)
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.85 and len(text) <= 60:
        return True
    if re.match(r"^(Chapter|CHAPTER|Parte|PARTE|Unit|UNIT|Lección|LECCIÓN)\b", text):
        return True
    if re.match(r"^(Exercise|Ejercicio|Reminder|Note|Nota)\b", text, re.I):
        return True
    return False


def looks_like_list_item(text: str) -> bool:
    return bool(
        re.match(
            r"^(\d+[\.\)]\s+|[-•●▪]\s+|[a-zA-Z][\.\)]\s+)",
            text,
        )
    )


def lines_to_markdown(lines) -> str:
    if not lines:
        return ""

    heights = [max(it["h"] for it in line) for line in lines if line is not None]
    mean_h = float(np.mean(heights)) if heights else 12.0

    md_parts = []
    para_buf = []

    def flush_para():
        nonlocal para_buf
        if para_buf:
            md_parts.append(" ".join(para_buf).strip())
            para_buf = []

    for line in lines:
        if line is None:  # layout block boundary
            flush_para()
            continue
        text = line_text(line)
        if is_page_noise(text):
            continue
        line_h = max(it["h"] for it in line)

        if looks_like_heading(text, mean_h, line_h):
            flush_para()
            # demote very long "headings"
            level = "##" if line_h >= mean_h * 1.5 or text.isupper() else "###"
            md_parts.append(f"{level} {text}")
            continue

        if looks_like_list_item(text):
            flush_para()
            # normalize bullet
            cleaned = re.sub(r"^[-•●▪]\s+", "- ", text)
            if not cleaned.startswith("- ") and not re.match(r"^\d+[\.\)]", cleaned):
                cleaned = f"- {cleaned}"
            md_parts.append(cleaned)
            continue

        # blank-ish gaps: short lines that look like labels stay separate
        if len(text) < 40 and text.endswith(":"):
            flush_para()
            md_parts.append(f"**{text}**")
            continue

        para_buf.append(text)

    flush_para()
    # join with blank lines between blocks
    out = []
    for i, part in enumerate(md_parts):
        out.append(part)
        if i < len(md_parts) - 1:
            out.append("")
    return "\n".join(out).strip() + ("\n" if md_parts else "")


def keep_awake():
    """Stop Windows from sleeping while a long conversion runs (released on exit)."""
    if sys.platform == "win32":
        import ctypes

        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


def orientation_score(reader, pil_image: Image.Image) -> float:
    """Confidence-weighted amount of text EasyOCR finds in the image."""
    results = reader.readtext(np.array(pil_image.convert("RGB")), detail=1, paragraph=False)
    return sum(conf * len((text or "").strip()) for _, text, conf in results)


def fix_orientation(reader, pil_image: Image.Image) -> tuple[Image.Image, bool]:
    """Detect pages scanned upside-down by OCR'ing a thumbnail both ways."""
    thumb = pil_image.copy()
    thumb.thumbnail((900, 900))
    upright = orientation_score(reader, thumb)
    flipped = orientation_score(reader, thumb.rotate(180))
    if flipped > upright * 1.2:
        return pil_image.rotate(180), True
    return pil_image, False


def ocr_page_image(reader, pil_image: Image.Image) -> list:
    """Raw EasyOCR results as JSON-friendly [[box, text, conf], ...]."""
    # EasyOCR expects RGB numpy array; detail=1 returns (bbox, text, conf)
    results = reader.readtext(np.array(pil_image.convert("RGB")), detail=1, paragraph=False)
    return [[[[float(x), float(y)] for x, y in box], text, float(conf)] for box, text, conf in results]


def layout_markdown(results: list, page_width: float) -> str:
    """Reading order + Markdown from raw OCR results (no OCR needed: re-runnable)."""
    if not results:
        return ""
    items = boxes_to_items([r[0] for r in results], [r[1] for r in results], [r[2] for r in results])
    if not items:
        return ""
    char_h = float(np.median([it["h"] for it in items]))
    blocks = drop_edge_blocks(xy_cut(items, char_h), page_width)
    lines = []
    for block in blocks:
        lines.extend(group_items_to_lines(block))
        lines.append(None)
    return lines_to_markdown(lines)


def convert_pdf_file(
    pdf_path: str,
    start_page: int | None,
    end_page: int | None,
    output_dir: str,
    scale: float = 2.0,
    languages: list[str] | None = None,
    auto_rotate: bool = False,
    relayout: bool = False,
):
    languages = languages or ["es", "en"]
    pdf_path = str(pdf_path)
    pdf_base = Path(pdf_path).stem
    pdf_output_dir = Path(output_dir) / pdf_base
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Local vision conversion: {Path(pdf_path).name} ---")
    print(f"Languages: {languages}")
    print(f"Render scale: {scale}")
    keep_awake()
    reader = None

    pdf = pdfium.PdfDocument(pdf_path)
    total_pages = len(pdf)
    start_idx = max(0, start_page - 1) if start_page else 0
    end_idx = min(total_pages, end_page) if end_page else total_pages

    print(f"Total pages: {total_pages}")
    print(f"Processing range: {start_idx + 1} .. {end_idx}")

    t_start = time.time()
    done_count = 0
    skip_count = 0

    for page_idx in range(start_idx, end_idx):
        page_num = page_idx + 1
        md_file_path = pdf_output_dir / f"page_{page_num:03d}.md"
        raw_file_path = pdf_output_dir / f"page_{page_num:03d}.json"

        if relayout and raw_file_path.exists():
            # Rebuild the Markdown from cached OCR boxes: seconds instead of minutes.
            cached = json.loads(raw_file_path.read_text(encoding="utf-8"))
            md = layout_markdown(cached["results"], cached["width"])
            md_file_path.write_text(md or f"<!-- empty OCR page {page_num} -->\n", encoding="utf-8")
            skip_count += 1
            continue

        if md_file_path.exists() and md_file_path.stat().st_size > 0 and raw_file_path.exists():
            skip_count += 1
            print(f"Page {page_num}/{end_idx} already exists. Skipping.")
            continue

        page_t0 = time.time()
        print(f"Converting page {page_num}/{end_idx}...", end="", flush=True)
        try:
            page = pdf[page_idx]
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            if auto_rotate:
                pil_image, rotated = fix_orientation(reader, pil_image)
                if rotated:
                    print(" [rotated 180°]", end="", flush=True)
            if reader is None:
                print(" [loading EasyOCR]", end="", flush=True)
                import easyocr

                reader = easyocr.Reader(languages, gpu=False, verbose=False)
            results = ocr_page_image(reader, pil_image)
            raw_file_path.write_text(
                json.dumps({"width": pil_image.width, "results": results}, ensure_ascii=False),
                encoding="utf-8",
            )
            markdown_content = layout_markdown(results, pil_image.width)
            if not markdown_content.strip():
                markdown_content = f"<!-- empty OCR page {page_num} -->\n"

            with open(md_file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            done_count += 1
            elapsed = time.time() - page_t0
            remaining = end_idx - page_num
            # rough ETA from average of newly done pages only
            avg = (time.time() - t_start) / max(done_count, 1)
            eta_min = (remaining * avg) / 60.0
            print(f" Done in {elapsed:.1f}s | ETA ~{eta_min:.0f} min")
        except Exception as e:
            print(f" ERROR: {e}")
            # leave no cache file so resume retries this page
            if md_file_path.exists():
                try:
                    md_file_path.unlink()
                except OSError:
                    pass
            time.sleep(1)

    pdf.close()

    # Combine pages in range
    combined_md_name = (
        f"{pdf_base}_vision_pages_{start_idx + 1}_{end_idx}.md"
        if (start_page or end_page)
        else f"{pdf_base}_vision.md"
    )
    combined_md_path = Path(pdf_path).parent / combined_md_name
    print(f"Combining pages into: {combined_md_path}")

    page_files = sorted(pdf_output_dir.glob("page_*.md"))
    in_range_files = []
    for pf in page_files:
        try:
            num = int(pf.stem.split("_")[1])
            if (start_idx + 1) <= num <= end_idx:
                in_range_files.append(pf)
        except (IndexError, ValueError):
            pass

    with open(combined_md_path, "w", encoding="utf-8") as outfile:
        outfile.write(f"# {pdf_base} (local vision OCR)\n\n")
        for page_file in in_range_files:
            page_n = Path(page_file).stem.split("_")[1]
            outfile.write(f"\n\n<!-- Page {page_n} -->\n\n")
            with open(page_file, "r", encoding="utf-8") as infile:
                outfile.write(infile.read().rstrip() + "\n")

    total_time = time.time() - t_start
    print(f"Finished. Converted {done_count} page(s), skipped {skip_count}.")
    print(f"Elapsed: {total_time / 60:.1f} min")
    print(f"Output: {combined_md_path}")
    return str(combined_md_path)


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown via local vision OCR (EasyOCR, no cloud)."
    )
    parser.add_argument("pdf_file", help="Path to the PDF file")
    parser.add_argument("--start", type=int, default=None, help="Start page (1-indexed)")
    parser.add_argument("--end", type=int, default=None, help="End page (1-indexed)")
    parser.add_argument("--scale", type=float, default=2.0, help="Render scale (default 2.0)")
    parser.add_argument(
        "--langs",
        type=str,
        default="es,en",
        help="Comma-separated EasyOCR language codes (default: es,en)",
    )
    parser.add_argument(
        "--auto-rotate",
        action="store_true",
        help="Detect and fix pages scanned upside-down (2 extra OCR passes per page). "
        "Not needed when the PDF stores the rotation itself, which pdfium already applies.",
    )
    parser.add_argument(
        "--relayout",
        action="store_true",
        help="Rebuild Markdown from cached raw OCR boxes (page_NNN.json) without re-running OCR",
    )
    args = parser.parse_args()

    if not os.path.exists(args.pdf_file):
        print(f"Error: File '{args.pdf_file}' does not exist.")
        sys.exit(1)

    cache_dir = os.path.join(os.path.dirname(os.path.abspath(args.pdf_file)), "conversion_cache_vision")
    langs = [x.strip() for x in args.langs.split(",") if x.strip()]
    convert_pdf_file(
        args.pdf_file,
        args.start,
        args.end,
        cache_dir,
        scale=args.scale,
        languages=langs,
        auto_rotate=args.auto_rotate,
        relayout=args.relayout,
    )


if __name__ == "__main__":
    main()
