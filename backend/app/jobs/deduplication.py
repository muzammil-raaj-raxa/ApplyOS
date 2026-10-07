import hashlib
import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import select

COMPANY_SUFFIXES = {
    "inc", "llc", "ltd", "limited", "corp", "corporation", "co", "gmbh", "plc",
    "sa", "ag", "bv", "pvt", "pte", "lp", "llp",
}
TRACKING_PARAMS = {"ref", "source", "src", "gh_src", "lever-source", "lever-origin"}
SIMILARITY_THRESHOLD = 0.92


def company_key(name: str) -> str:
    """'Stripe, Inc.' -> 'stripe'"""
    words = re.sub(r"[^a-z0-9 ]+", " ", name.lower()).split()
    kept = [w for w in words if w not in COMPANY_SUFFIXES]
    if len(kept) > 1 and kept[0] == "the":
        kept = kept[1:]
    return "".join(kept or words)


def title_key(title: str) -> str:
    """'Sr. iOS Engineer (Remote)' -> 'senior ios engineer'"""
    text = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", " ", title.lower())
    text = re.sub(r"\bsr\b\.?", "senior", text)
    text = re.sub(r"\bjr\b\.?", "junior", text)
    text = re.sub(r"[^a-z0-9+# ]+", " ", text)
    return " ".join(text.split())


def location_key(location: str | None) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", (location or "").lower()).split())


def canonical_url(url: str) -> str:
    """Same job, same URL: lowercase host, no tracking params, no trailing slash."""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    query = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMS
    )
    return urlunsplit(("https", host, path, urlencode(query), ""))


def make_fingerprint(company: str, title: str, url: str) -> str:
    raw = f"{company_key(company)}|{title_key(title)}|{canonical_url(url)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _locations_compatible(a: str, b: str) -> bool:
    return not a or not b or a == b or a in b or b in a


class DedupIndex:
    """Remembers every job seen so far. Same fingerprint is a duplicate. A similar job
    from a DIFFERENT source (same company, near-identical title, compatible location)
    is also a duplicate. Same-source jobs with different URLs stay separate, because
    one company can post several openings with the same title."""

    def __init__(self):
        self._fingerprints: set[str] = set()
        self._entries: dict[str, list[tuple[str, str, str]]] = {}

    @classmethod
    def from_session(cls, session) -> "DedupIndex":
        from app.database.models import Job

        index = cls()
        rows = session.execute(
            select(Job.fingerprint, Job.source, Job.company, Job.title, Job.location)
        ).all()
        for fingerprint, source, company, title, location in rows:
            index.add(fingerprint, source, company_key(company), title_key(title), location_key(location))
        return index

    def add(self, fingerprint: str, source: str, ckey: str, tkey: str, lkey: str) -> None:
        self._fingerprints.add(fingerprint)
        self._entries.setdefault(ckey, []).append((source, tkey, lkey))

    def check(self, fingerprint: str, source: str, ckey: str, tkey: str, lkey: str) -> str | None:
        """Returns why this job is a duplicate, or None if it is new."""
        if fingerprint in self._fingerprints:
            return "already stored"
        for other_source, other_title, other_location in self._entries.get(ckey, []):
            if other_source == source:
                continue
            if _locations_compatible(lkey, other_location):
                if SequenceMatcher(None, tkey, other_title).ratio() >= SIMILARITY_THRESHOLD:
                    return f"same job already found via {other_source}"
        return None
