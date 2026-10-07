import html
import re

from app.jobs.deduplication import company_key, location_key, make_fingerprint, title_key
from app.jobs.schemas import NormalizedJob, RawJob
from app.jobs.skills_vocab import SKILLS

# ---------- text cleanup ----------


def _collapse(value: str | None) -> str:
    return " ".join((value or "").split())


def html_to_text(value: str | None) -> str:
    """HTML (or Greenhouse's HTML-escaped HTML) -> readable plain text with line breaks."""
    if not value:
        return ""
    text = value
    for _ in range(2):  # Greenhouse sends escaped HTML, sometimes escaped twice
        if "&lt;" in text or "&amp;lt;" in text:
            text = html.unescape(text)
    text = re.sub(r"(?i)<li[^>]*>", "\n- ", text)
    text = re.sub(r"(?i)<br\s*/?>|</(?:p|div|li|h[1-6]|ul|ol|tr|section)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------- workplace ----------

_HINTS = {"remote": "remote", "hybrid": "hybrid", "on-site": "onsite", "onsite": "onsite",
          "on site": "onsite", "in-office": "onsite", "office": "onsite"}

_DESC_REMOTE = re.compile(
    r"fully remote|100% remote|remote[- ]first|work from anywhere|this is a remote|"
    r"remote position|remote role|remote-eligible",
    re.IGNORECASE,
)
_DESC_HYBRID = re.compile(
    r"hybrid (?:work|role|position|schedule|model|environment)|"
    r"(?:\d|one|two|three|four)\s+days? (?:a|per) week in (?:the )?office",
    re.IGNORECASE,
)
_DESC_ONSITE = re.compile(
    r"on-?site (?:role|position|only)|(?:five|5) days (?:a|per) week in (?:the )?office|"
    r"this role is on-?site",
    re.IGNORECASE,
)


def detect_workplace(title: str, location: str | None, description: str, hint: str | None) -> str:
    """remote / hybrid / onsite / unknown. A hint from the source wins."""
    if hint:
        mapped = _HINTS.get(hint.strip().lower())
        if mapped:
            return mapped
    head = f"{title} {location or ''}".lower()
    if "hybrid" in head:
        return "hybrid"
    if "remote" in head:
        return "remote"
    if _DESC_HYBRID.search(description):
        return "hybrid"
    if _DESC_REMOTE.search(description):
        return "remote"
    if _DESC_ONSITE.search(description):
        return "onsite"
    return "unknown"


def remote_flag(workplace: str) -> bool | None:
    if workplace == "remote":
        return True
    if workplace in ("hybrid", "onsite"):
        return False
    return None


# ---------- salary ----------

_NUMBER = r"\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d+)?\s?[kK]"
_CURRENCY = r"[$£€]|USD|GBP|EUR|CAD|AUD"
_SALARY = re.compile(
    rf"(?P<cur>{_CURRENCY})\s?(?P<a>{_NUMBER})\s*(?:-|–|—|to)\s*(?:{_CURRENCY})?\s?(?P<b>{_NUMBER})"
)
_SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR"}


def _to_number(value: str) -> int:
    value = value.replace(",", "").replace(" ", "")
    if value[-1] in "kK":
        return int(float(value[:-1]) * 1000)
    return int(float(value))


def extract_salary(text: str) -> tuple[int | None, int | None, str | None]:
    """First annual-looking salary range with a currency. Hourly-looking numbers are skipped."""
    for match in _SALARY.finditer(text):
        low, high = _to_number(match.group("a")), _to_number(match.group("b"))
        if low > high:
            low, high = high, low
        if low >= 20_000:
            currency = match.group("cur")
            return low, high, _SYMBOLS.get(currency, currency)
    return None, None, None


# ---------- experience, sponsorship, employment type ----------

_YEARS = re.compile(r"(\d{1,2})\s*(?:\+|plus)?(?:\s*(?:-|–|to)\s*\d{1,2})?\s*\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)


def extract_min_years(text: str) -> int | None:
    """Largest 'N+ years ... experience' found. The binding minimum is the largest one."""
    best = None
    for match in _YEARS.finditer(text):
        context = text[max(0, match.start() - 80): match.end() + 80].lower()
        if "experience" not in context:
            continue
        years = int(match.group(1))
        if 0 < years <= 25:
            best = years if best is None else max(best, years)
    return best


_NO_SPONSOR = re.compile(
    r"(?:unable|not able|cannot|can't|won't|will not|do not|does not|don't|doesn't)\s+(?:\w+\s+){0,3}sponsor|"
    r"no (?:visa )?sponsorship|sponsorship (?:is )?not (?:available|offered|provided)|"
    r"without (?:the need for )?(?:visa )?sponsorship|"
    r"must (?:already )?be (?:legally )?authori[sz]ed to work",
    re.IGNORECASE,
)
_YES_SPONSOR = re.compile(
    r"(?:visa )?sponsorship (?:is )?(?:available|offered|provided)|"
    r"we (?:can|will|do) sponsor|sponsor(?:s)? (?:work )?visas?",
    re.IGNORECASE,
)


def detect_sponsorship(text: str) -> str:
    if _NO_SPONSOR.search(text):
        return "not_available"
    if _YES_SPONSOR.search(text):
        return "available"
    return "unknown"


def detect_employment_type(hint: str | None, title: str, description: str) -> str | None:
    probes = [(hint or "").lower(), title.lower()]
    for probe in probes:
        if re.search(r"intern", probe):
            return "internship"
        if re.search(r"part[-_ ]?time", probe):
            return "part-time"
        if re.search(r"full[-_ ]?time|permanent", probe):
            return "full-time"
        if re.search(r"contract|freelance|fixed[-_ ]term|temporary|temp\b", probe):
            return "contract"
    if re.search(r"(?:this is a|position is a|role is a)\s+full[- ]time", description, re.IGNORECASE):
        return "full-time"
    return None


# ---------- skills ----------

_PREFERRED_HEADING = re.compile(
    r"nice[- ]to[- ]have|preferred|bonus|a plus|good to have|desirable|extra credit|ideal", re.IGNORECASE
)
_REQUIRED_HEADING = re.compile(
    r"requirements?|qualifications?|what you(?:'ll| will)? (?:need|bring|do)|about you|must[- ]have|"
    r"you have|minimum|who you are|responsibilities|the role|about the (?:role|job)",
    re.IGNORECASE,
)
_INLINE_PREFERRED = re.compile(
    r"nice to have|is a plus|are a plus|a big plus|\bplus\b|bonus|preferred|ideally|a strong plus",
    re.IGNORECASE,
)


def _is_heading(line: str) -> bool:
    if line.startswith(("-", "*", "•")) or len(line) > 70:
        return False
    return line.endswith(":") or not re.search(r"[.!?]\s|[.!?]$", line)


def extract_skills(title: str, description: str) -> tuple[list[str], list[str]]:
    """(required, preferred). A skill is preferred only if it never appears in a required spot."""
    required: list[str] = []
    preferred: list[str] = []

    def record(line: str, bucket_name: str) -> None:
        for name, pattern in SKILLS:
            if pattern.search(line):
                if bucket_name == "required":
                    if name not in required:
                        required.append(name)
                elif name not in preferred:
                    preferred.append(name)

    record(title, "required")
    mode = "required"
    for raw_line in description.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _is_heading(line):
            if _PREFERRED_HEADING.search(line):
                mode = "preferred"
            elif _REQUIRED_HEADING.search(line):
                mode = "required"
            continue
        line_mode = "preferred" if mode == "preferred" or _INLINE_PREFERRED.search(line) else "required"
        record(line, line_mode)
    preferred = [name for name in preferred if name not in required]
    return required, preferred


# ---------- main entry point ----------


def normalize(raw: RawJob) -> NormalizedJob:
    """RawJob -> NormalizedJob. Raises ValueError only if title, company or URL is missing."""
    title = _collapse(raw.title)
    company = _collapse(raw.company)
    url = (raw.url or "").strip()
    if not (title and company and url):
        raise ValueError("job is missing a title, company, or URL")

    problems: list[str] = []
    description = html_to_text(raw.description)
    if not description:
        problems.append("empty description")
    location = _collapse(raw.location) or None

    workplace = detect_workplace(title, location, description, raw.workplace_hint)
    if raw.salary_min is not None and raw.salary_max is not None:
        salary_min, salary_max, currency = raw.salary_min, raw.salary_max, raw.salary_currency
    else:
        salary_min, salary_max, currency = extract_salary(description)
    employment_type = detect_employment_type(raw.employment_hint, title, description)
    required, preferred = extract_skills(title, description)
    remote = remote_flag(workplace)

    requirements = {
        "required_skills": required,
        "preferred_skills": preferred,
        "minimum_years": extract_min_years(description),
        "remote": remote,
        "workplace": workplace,
        "sponsorship": detect_sponsorship(description),
        "employment_type": employment_type,
        "salary_currency": currency,
    }
    return NormalizedJob(
        title=title,
        company=company,
        location=location,
        remote=remote,
        workplace=workplace,
        url=url,
        description=description,
        source=raw.source,
        external_id=raw.external_id,
        posted_date=raw.posted_date,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=currency,
        employment_type=employment_type,
        requirements=requirements,
        company_key=company_key(company),
        title_key=title_key(title),
        location_key=location_key(location),
        fingerprint=make_fingerprint(company, title, url),
        parsing_error="; ".join(problems) or None,
    )
