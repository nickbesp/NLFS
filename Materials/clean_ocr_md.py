"""Rule-based cleanup of Tesseract OCR Markdown (Spanish textbooks).

Reads the raw OCR Markdown from DeLe_B2/ocr_output/ and writes cleaned copies
next to the original PDFs. The raw files stay untouched as backups.

Fixes: ¿/¡ misreads, bullet symbols, missing accents (via word frequencies),
hyphenated line breaks, wrapped lines, blank-line runs, and noise lines.
"""

import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.request import urlretrieve

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent / "DeLe_B2"
RAW = BASE / "ocr_output"
FREQ_URL = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/es/es_50k.txt"
FREQ_FILE = Path(__file__).parent / "es_50k.txt"

# Where each cleaned book goes (matched by filename prefix; names have decomposed accents).
TARGETS = {
    "Grama": BASE,
    "Prepara": BASE,
    "Viva": BASE,
    "Vocabulario-activo": BASE / "El_Libro",
    "Aula_2": BASE / "El_Libro",
    "Aula_4": BASE / "El_Libro",
}

# Valid unaccented words whose accented twin is also valid: never auto-accent these.
PROTECTED = set("""
esta este estas estos ese esa esos esas aquel aquella aquellos aquellas eso esto
mas si se el tu mi te de que como cuando donde quien quienes cual cuales cuanto cuanta
cuantos cuantas solo aun publico practico termino ultimo ultima continuo critico
animo transito deposito liquido limite numero calculo medico titulo vinculo
hablo llego paso pago gano canto estudio trabajo envio cambio entro saco toco
hacia sabia tenia podia habia seria seria vivia comia
""".split())

ACCENTS = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "n": "ñ"}
FIXED = {"mds": "más", "mads": "más", "rads": "más"}

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")
BULLET_RE = re.compile(r"^\s*(?:[M\"=*©•®«»]|ee?|[-—]+|\.)\s+(?=\S)")
BLANK_RE = re.compile(r"(?:[—_–]\s*){3,}|\.{4,}|…{2,}")


def load_freq():
    if not FREQ_FILE.exists():
        urlretrieve(FREQ_URL, FREQ_FILE)
    freq = {}
    for line in FREQ_FILE.read_text(encoding="utf-8").splitlines():
        w, n = line.rsplit(" ", 1)
        freq[unicodedata.normalize("NFC", w)] = int(n)
    return freq


def match_case(src, word):
    if src.isupper() and len(src) > 1:
        return word.upper()
    if src[0].isupper():
        return word[0].upper() + word[1:]
    return word


class Fixer:
    def __init__(self, freq):
        self.freq = freq
        self.changes = Counter()

    def accent(self, m):
        src = m.group(0)
        low = src.lower()
        if low in FIXED:
            self.changes[(src, FIXED[low])] += 1
            return match_case(src, FIXED[low])
        if len(low) < 3 or low in PROTECTED or any(c in low for c in "áéíóúñü"):
            return src
        own = self.freq.get(low, 0)
        best, best_n = None, 0
        for i, c in enumerate(low):
            # An accent on the final vowel often makes a different valid word
            # (hablara/hablará, hablo/habló): only allow it for unknown words,
            # and never for -ra/-re subjunctive-looking endings.
            if i == len(low) - 1 and (own > 0 or re.search(r"r[ae]s?$", low)):
                continue
            if i == len(low) - 2 and low.endswith("s") and re.search(r"r[ae]s$", low):
                continue
            if c in ACCENTS:
                cand = low[:i] + ACCENTS[c] + low[i + 1:]
                n = self.freq.get(cand, 0)
                if n > best_n:
                    best, best_n = cand, n
        # Unknown word with a known accented twin, or a twin that is far more common.
        if best and (own == 0 or best_n >= 20 * own):
            fixed = match_case(src, best)
            self.changes[(src, fixed)] += 1
            return fixed
        return src

    def is_noise(self, line):
        s = line.strip()
        if len(s) < 4 or s.startswith("#"):
            return False
        letters = sum(ch.isalpha() for ch in s)
        content = s.replace("____", "")
        if letters / max(1, len(content)) < 0.35 and not re.search(r"\d|____", s):
            return True
        words = [w.lower() for w in WORD_RE.findall(s) if len(w) >= 3]
        if len(words) >= 4:
            known = sum(w in self.freq for w in words)
            if known / len(words) < 0.25:
                return True
        return False

    def fix_line(self, line):
        line = BLANK_RE.sub("____ ", line).rstrip()
        line = BULLET_RE.sub("- ", line)
        # ¿ misread as { « i or ¢ before a question; ¡ misread as i/j before an exclamation.
        line = re.sub(r"(^|[\s(\-—])[{«¢]\s?(?=[A-ZÁÉÍÓÚa-záéíóú][^?]*\?)", r"\1¿", line)
        line = re.sub(r"(^|[\s(\-—])i(?=[A-ZÁÉÍÓÚ][^?\s]*[^?]*\?)", r"\1¿", line)
        line = re.sub(r"(^|[\s(\-—])[ij](?=[A-ZÁÉÍÓÚ][^!\s]*[^!]*!)", r"\1¡", line)
        return WORD_RE.sub(self.accent, line)


def clean_page(text, fixer):
    # Join words hyphenated across line breaks.
    text = re.sub(r"([a-záéíóúñü])-\n([a-záéíóúñü])", r"\1\2", text)
    out, dropped = [], 0
    for line in text.split("\n"):
        line = BLANK_RE.sub("____ ", line)
        if fixer.is_noise(line):
            dropped += 1
            continue
        line = fixer.fix_line(line)
        prev = out[-1] if out else ""
        # Merge a wrapped line into the previous one when it clearly continues it.
        if (prev and line and line[0].islower() and not prev.startswith("#")
                and not re.search(r"[.:?!»)\]]$", prev)):
            out[-1] = prev + " " + line.lstrip()
        else:
            out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip(), dropped


def main():
    fixer = Fixer(load_freq())
    for src in sorted(RAW.glob("*.md")):
        dest_dir = next(d for p, d in TARGETS.items() if src.name.startswith(p))
        raw = unicodedata.normalize("NFC", src.read_text(encoding="utf-8"))
        # Keep the "# title" / "## Página N" structure produced by run_ocr.py.
        chunks = re.split(r"(^## Página \d+\n)", raw, flags=re.M)
        before = sum(fixer.changes.values())
        dropped = 0
        parts = [chunks[0].strip() + "\n"]
        for head, body in zip(chunks[1::2], chunks[2::2]):
            body, d = clean_page(body, fixer)
            dropped += d
            parts.append(f"{head}\n{body}\n")
        (dest_dir / src.name).write_text("\n".join(parts), encoding="utf-8")
        print(f"{src.name[:45]:45s} accent fixes {sum(fixer.changes.values()) - before:5d} | noise lines dropped {dropped:5d}")
    print("\nMost frequent word fixes:")
    for (a, b), n in fixer.changes.most_common(40):
        print(f"  {n:5d}  {a} -> {b}")


if __name__ == "__main__":
    main()
