from typing import Dict, List, Tuple
from rapidfuzz import fuzz, process  # pip install rapidfuzz

# Canonical keys → synonyms we look for
KNOWN = {
    "first_name": ["first name", "firstname", "given-name", "given_name"],
    "last_name": ["last name", "lastname", "family-name", "surname"],
    "email": ["email", "e-mail", "Email address"],
    "password": ["password", "pass"],
    "phone": ["phone", "mobile", "tel"],
    "username": ["username", "user name", "login"],
    "birthday_day": ["day", "dd"],
    "birthday_month": ["month", "mm"],
    "birthday_year": ["year", "yyyy"],
    # add more as you need
}


def _best_key(label: str) -> str | None:
    """Return the canonical key whose synonym best matches *label*."""
    label = label.lower()
    best, score = process.extractOne(
        label,
        [(k, syn) for k, syns in KNOWN.items() for syn in syns],
        scorer=fuzz.partial_ratio,
    )  # returns ((canonical,synonym), score)
    if score >= 80:  # tweak threshold
        return best[0]
    return None


def auto_build_mapping(self, page) -> Dict[str, str]:
    """Scan DOM, return {canonical_key: css_selector}"""
    mapping = {}
    # grab every fieldlike element
    elements = page.query_selector_all("input, select, textarea")
    for el in elements:
        # Assemble as many human hints as we can
        label_text = page.evaluate(
            """
            el => {
              const l = (
                  (el.labels && el.labels[0]?.innerText) ||  // paired <label>
                  el.getAttribute('aria-label')             ||
                  el.placeholder                             ||
                  el.name                                    ||
                  ''
              ).trim();
              return l;
            }
            """,
            el,
        )
        key = _best_key(label_text)
        if not key:
            continue

        # make a unique selector Playwright can re-use
        selector = el.eval("el => el.id ? `#${el.id}` : el.outerHTML")
        mapping[key] = selector
    return mapping


# utils.py  (put it anywhere that is imported early – e.g. top of form_filler_agent.py)
from pathlib import Path
import sys, os
import sys, shutil


def resource_path(rel_path: str | os.PathLike) -> Path:
    """
    Return an absolute Path to *rel_path* whether we are running
    from source or from a PyInstaller bundle.
    """
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return Path(base, rel_path)


# utils.py  ─────────────────────────────────────────────────────────


def bundle_root() -> Path:
    """Folder that contains JARVIS.exe when frozen, or cwd when not."""
    if getattr(sys, "frozen", False):          # running from PyInstaller bundle
        return Path(sys.executable).parent     # …/dist/JARVIS
    return Path(__file__).resolve().parent     # normal dev run

def copy_to_internal(src: Path):
    """Duplicate *src* into the _internal runtime folder."""
    if getattr(sys, "frozen", False):
        internal = Path(sys._MEIPASS) / src.name   # …/dist/JARVIS/_internal
        try:
            shutil.copy2(src, internal)
        except Exception as exc:
            # non-fatal – just print for diagnostics
            print("⚠️  could not copy to _internal:", exc)


# paths.py  ───────────────────────────────────────────────
from pathlib import Path
import sys

def bundle_root12() -> Path:
    """
    Return the folder that contains the executable when frozen,
    else the project root when running from source.
    """
    if getattr(sys, "frozen", False):               # PyInstaller sets this
        return Path(sys.executable).parent          # …\dist\JARVIS
    return Path(__file__).resolve().parent

def resource_path12(name: str) -> Path:
    """
    Locate *read-only* files shipped with the app
    (JSON, images, DLLs…)  no matter where PyInstaller put them.
    """
    root = bundle_root()
    # first look right next to the EXE, then inside _internal
    direct = root / name
    internal = root / "_internal" / name
    if direct.exists():
        return direct
    return internal        # PyInstaller keeps it here in “standard” mode
