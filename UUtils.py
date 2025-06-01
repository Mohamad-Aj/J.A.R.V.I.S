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
