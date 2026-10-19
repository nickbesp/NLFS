"""Book-specific restructuring for '501 Spanish Verbs' (output of convert_pdf_text_md.py).

Each verb page becomes a self-contained section, which is what a RAG index wants:
- the verb, its number, English meaning, gerund and past participle are gathered
  from wherever pdfium placed them and written as the page heading
  ("## abrir (4) — to open");
- tense rows "1 presente de indicativo abro abrimos abres abrís abre abren"
  (singular/plural interleaved, as printed in two columns) are rewritten as
  "1 presente de indicativo: abro, abres, abre | abrimos, abrís, abren";
- the printer's slug line ("7_3559_Spanish_001_252 10/19/06 5:18 PM Page 100") is removed.
Pages that are not verb pages are only stripped of the slug.

Usage:
    python restructure_501_verbs.py IN.md OUT.md
"""

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

W = r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]"
# "7_3559_Spanish_001_252 10/19/06 5:18 PM Page 100", "7-7984-501SpanVrbs-Fbs ...", "Blank ...";
# it can be glued to the end of real text ("numerical rank7_3559_...")
SLUG_RE = re.compile(r"(?:\d[\w-]*|\bBlank)\s+\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s*[AP]M\s+Page\s+[\divxlc]+\s*$")
TENSES = [
    "presente de indicativo", "imperfecto de indicativo", "pretérito", "futuro",
    "potencial simple", "presente de subjuntivo", "imperfecto de subjuntivo",
    "perfecto de indicativo", "pluscuamperfecto de indicativo", "pretérito anterior",
    "futuro perfecto", "potencial compuesto", "perfecto de subjuntivo",
    "pluscuamperfecto de subjuntivo",
]
TENSE_RE = re.compile(rf"^(\d{{1,2}}) ({'|'.join(sorted(map(re.escape, TENSES), key=len, reverse=True))}) (.+)$")
VERB_RE = re.compile(rf"\b({W}+(?:se)?) \((\d{{1,3}})\)")
GERUND_RE = re.compile(rf"Gerundio ({W}+)")
PARTICIPLE_RE = re.compile(rf"Part\.\s*(?:pas\.)?\s*({W}+)")
MEANING_RE = re.compile(r"^(to [^|]+?)(?:\s+imperativo)?$")


def six_forms(forms: str):
    """Split 6 interleaved forms (sg1 pl1 sg2 pl2 sg3 pl3) into singular | plural."""
    words = forms.split()
    if len(words) % 6:
        return None
    n = len(words) // 6
    f = [" ".join(words[i * n:(i + 1) * n]) for i in range(6)]
    return f"{f[0]}, {f[2]}, {f[4]} | {f[1]}, {f[3]}, {f[5]}"


def restructure_page(body: str) -> str:
    # the slug can be glued to real text ("...numerical rank7_3559_Spanish_FM1 10/20/06 ...
    # Page 1"): cut the slug, keep the text
    lines = [SLUG_RE.sub("", l) for l in body.split("\n")]
    lines = [l for l in lines if l.strip() or not l]
    text = "\n".join(lines)
    if "presente de indicativo" not in text or not VERB_RE.search(text):
        return "\n".join(lines).strip()

    verb, number = VERB_RE.search(text).groups()
    gerund = GERUND_RE.search(text)
    participle = PARTICIPLE_RE.search(text)
    meaning = None
    # the title is sometimes glued to the end of a tense row ("... hubiesen abierto
    # abrir (4) Gerundio ..."): put it on its own line first
    marker = f"{verb} ({number})"
    split_lines = []
    for l in lines:
        i = l.find(marker)
        if i > 0 and l[:i].strip():
            split_lines += [l[:i].rstrip(), l[i:]]
        else:
            split_lines.append(l)
    out = []
    for l in split_lines:
        s = l.strip()
        m = MEANING_RE.match(s)
        if m and meaning is None:
            meaning = m.group(1).strip()
            if s.endswith("imperativo"):
                out.append("imperativo")
            continue
        # the header fragments ("abrir (4) Gerundio abriendo Part.") go into the heading
        if "Gerundio" in s or re.fullmatch(rf"(?:Part\.\s*)?(?:pas\.\s*{W}+\s*)?{re.escape(verb)} \({number}\)", s):
            rest = VERB_RE.sub("", GERUND_RE.sub("", PARTICIPLE_RE.sub("", s)))
            rest = re.sub(r"\bPart\.|\bpas\.", "", rest).strip()
            m = re.match(r"(to .+?)(\s+imperativo)?$", rest)
            if m and meaning is None:
                meaning = m.group(1).strip()
                if m.group(2):
                    out.append("imperativo")
            elif rest:
                out.append(rest)
            continue
        t = TENSE_RE.match(s)
        if t:
            num, tense, forms = t.groups()
            split = six_forms(forms)
            out.append(f"{num} {tense}: {split}" if split else s)
            continue
        if s.startswith("OR "):
            split = six_forms(s[3:])
            out.append(f"OR: {split}" if split else s)
            continue
        out.append(l)

    head = f"## {verb} ({number})" + (f" — {meaning}" if meaning else "")
    forms = []
    if gerund:
        forms.append(f"Gerundio: {gerund.group(1)}")
    if participle:
        forms.append(f"Participio pasado: {participle.group(1)}")
    header = [head, ""] + ([" · ".join(forms), ""] if forms else [])
    return re.sub(r"\n{3,}", "\n\n", "\n".join(header + out)).strip()


def main():
    src, dst = sys.argv[1], sys.argv[2]
    text = Path(src).read_text(encoding="utf-8")
    parts = re.split(r"^(<!-- (?:Página \d+|Portada \(PDF \d+\)) -->)$", text, flags=re.M)
    out = [parts[0]]
    verbs = 0
    for marker, body in zip(parts[1::2], parts[2::2]):
        new = restructure_page(body)
        verbs += new.startswith("## ")
        out.append(f"{marker}\n\n{new}\n\n" if new else f"{marker}\n\n")
    Path(dst).write_text("".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"Pages: {len(parts) // 2} | verb pages restructured: {verbs}")


if __name__ == "__main__":
    main()
