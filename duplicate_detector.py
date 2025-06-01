# duplicate_detector_debug.py  ←  rename if you like
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import asyncio, textwrap, sys
from dotenv import load_dotenv

load_dotenv()

import openai
from docx import Document
from PyPDF2 import PdfReader  # ONLY PyPDF2, as you asked

# ── SETTINGS ───────────────────────────────────────────────────────────
OPENAI_MODEL = "gpt-4o-mini"
MAX_CHARS_SEND = 4_000
SIZE_TOLERANCE = 0.30
ALLOWED_EXTS = {".txt", ".pdf", ".docx"}
CONCURRENCY = 4

DEBUG = True  # ← flip to False when it finally works
# ───────────────────────────────────────────────────────────────────────


def _dbg(msg: str):
    if DEBUG:
        print(msg, file=sys.stderr)


# ── extraction helpers ────────────────────────────────────────────────
def _extract_txt(p: Path, lim: int) -> str:
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")[:lim]
    except Exception:
        txt = p.read_text(errors="ignore")[:lim]
    _dbg(f"[TXT] {p.name}: {len(txt)} chars")
    return txt


def _extract_pdf(p: Path, lim: int) -> str:
    try:
        reader = PdfReader(str(p))
        if getattr(reader, "is_encrypted", False):
            reader.decrypt("")  # blank password best-effort
            _dbg(f"[PDF] {p.name} was encrypted → tried blank pwd")

        parts, so_far = [], 0
        for i, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            parts.append(txt)
            so_far += len(txt)
            _dbg(f"      page {i+1}: {len(txt)} chars")
            if so_far >= lim:
                break
        joined = " ".join(parts)[:lim]
        _dbg(f"[PDF] {p.name}: TOTAL {len(joined)} chars kept\n")
        return joined
    except Exception as e:
        _dbg(f"[PDF] {p.name}: ERROR → {e}\n")
        return ""


def _extract_docx(p: Path, lim: int) -> str:
    try:
        doc = Document(str(p))
        txt = " ".join(par.text for par in doc.paragraphs)[:lim]
        _dbg(f"[DOCX] {p.name}: {len(txt)} chars")
        return txt
    except Exception as e:
        _dbg(f"[DOCX] {p.name}: ERROR → {e}")
        return ""


def _extract(p: Path, lim: int = MAX_CHARS_SEND) -> str:
    ext = p.suffix.lower()
    if ext == ".txt":
        return _extract_txt(p, lim)
    if ext == ".pdf":
        return _extract_pdf(p, lim)
    if ext == ".docx":
        return _extract_docx(p, lim)
    return ""


# ── GPT helper ────────────────────────────────────────────────────────
def _prompt(a_txt: str, b_txt: str, ext: str) -> str:
    return (
        f"Decide if two {ext.upper()} files are DUPLICATE, SIMILAR or DIFFERENT. "
        f"Answer with ONE WORD only.\n\n"
        f"--- FILE A (truncated) ---\n{a_txt}\n\n"
        f"--- FILE B (truncated) ---\n{b_txt}"
    )


async def _gpt(cli: openai.AsyncClient, a: Path, b: Path) -> str:
    txt_a, txt_b = _extract(a), _extract(b)

    # fallback for empty-text PDFs that happen to be byte-identical
    if a.suffix.lower() == b.suffix.lower() == ".pdf" and not txt_a and not txt_b:
        if a.stat().st_size == b.stat().st_size:
            _dbg(f"[FALLBACK] {a.name} & {b.name} same byte-size → DUPLICATE")
            return "DUPLICATE"

    rsp = await cli.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": _prompt(txt_a, txt_b, a.suffix)}],
        timeout=25,
    )
    word = rsp.choices[0].message.content.strip().split()[0].upper()
    _dbg(f"[GPT] {a.name} ↔ {b.name}  →  {word}")
    return (
        "DUPLICATE"
        if word.startswith("DU")
        else "SIMILAR" if word.startswith("SI") else "DIFFERENT"
    )


# ── public class ──────────────────────────────────────────────────────
class DuplicateDetector:
    def __init__(self, api_key: str):
        self.client = openai.AsyncClient(api_key=api_key)

    async def scan(
        self, root: Path
    ) -> Tuple[List[Tuple[Path, Path]], List[Tuple[Path, Path]]]:

        files = [
            p
            for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in ALLOWED_EXTS
        ]
        _dbg(f"\n=== SCANNING {root}   ({len(files)} eligible files) ===")

        buckets: dict[str, List[Path]] = {}
        for f in files:
            buckets.setdefault(f.suffix.lower(), []).append(f)

        exact, similar = [], []
        sem = asyncio.Semaphore(CONCURRENCY)
        tasks = []

        async def judge(a: Path, b: Path):
            async with sem:
                v = await _gpt(self.client, a, b)
            if v == "DUPLICATE":
                exact.append((a, b))
            elif v == "SIMILAR":
                similar.append((a, b))

        for grp in buckets.values():
            grp.sort(key=lambda p: p.stat().st_size)
            for i, a in enumerate(grp):
                for b in grp[i + 1 :]:
                    sa, sb = a.stat().st_size, b.stat().st_size
                    if abs(sa - sb) / max(sa, sb) > SIZE_TOLERANCE:
                        continue
                    tasks.append(judge(a, b))

        await asyncio.gather(*tasks)
        _dbg(f"=== DONE: {len(exact)} exact · {len(similar)} similar ===\n")
        return exact, similar
