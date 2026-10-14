"""Visita el sitio de cada prospecto y extrae datos de contacto públicos."""
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .search import HEADERS

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Teléfonos mexicanos: +52, lada de 2-3 dígitos y 7-8 dígitos, con separadores variados.
PHONE_RE = re.compile(r"(?:\+?52[\s.-]?)?(?:\(?\d{2,3}\)?[\s.-]?)\d{3,4}[\s.-]?\d{4}")
WHATSAPP_RE = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\+?\d{10,13})")
LINKEDIN_RE = re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9_\-%]+/?")

CONTACT_HINTS = ("contact", "contacto", "nosotros", "about", "equipo", "team")
BAD_EMAIL_PARTS = ("example", "sentry", "wixpress", "domain.com", "email.com", "@2x", ".png", ".jpg", ".webp", ".svg")


def domain_of(url):
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def fetch(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code >= 400 or "text/html" not in r.headers.get("Content-Type", ""):
            return None
        return r.text
    except requests.RequestException:
        return None


def extract_contacts(html, base_url=""):
    """Saca emails, teléfonos, WhatsApp, LinkedIn y links a páginas de contacto de un HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    hrefs = [a.get("href", "") for a in soup.find_all("a")]
    raw = text + " " + " ".join(hrefs)

    emails = set()
    for h in hrefs:
        if h.lower().startswith("mailto:"):
            emails.add(h[7:].split("?")[0].strip())
    emails.update(EMAIL_RE.findall(text))
    emails = {e.lower().strip(".") for e in emails if _good_email(e)}

    phones = set()
    for h in hrefs:
        if h.lower().startswith("tel:"):
            phones.add(normalize_phone(h[4:]))
    for m in PHONE_RE.findall(text):
        p = normalize_phone(m)
        if p:
            phones.add(p)
    phones.discard(None)

    whatsapp = {normalize_phone(m) for m in WHATSAPP_RE.findall(raw)} - {None}
    linkedin = set(LINKEDIN_RE.findall(raw))

    contact_pages = []
    for h in hrefs:
        if any(k in h.lower() for k in CONTACT_HINTS) and not h.startswith(("mailto:", "tel:", "#")):
            full = urljoin(base_url, h)
            if domain_of(full) == domain_of(base_url):
                contact_pages.append(full)

    title = soup.title.get_text(strip=True) if soup.title else ""
    desc = soup.find("meta", attrs={"name": "description"})
    return {
        "emails": sorted(emails),
        "phones": sorted(phones),
        "whatsapp": sorted(whatsapp),
        "linkedin": sorted(linkedin),
        "contact_pages": list(dict.fromkeys(contact_pages))[:2],
        "title": title,
        "description": desc.get("content", "").strip() if desc else "",
        "text": text[:5000],
    }


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("52") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("521") and len(digits) == 13:
        digits = digits[3:]
    if len(digits) != 10 or len(set(digits)) <= 2:
        return None
    return f"+52 {digits[:2]} {digits[2:6]} {digits[6:]}"


def _good_email(e):
    e = e.lower()
    return not any(b in e for b in BAD_EMAIL_PARTS) and len(e) < 80


def enrich(url):
    """Visita la home y hasta dos páginas de contacto. Devuelve los datos juntos."""
    html = fetch(url)
    if not html:
        return None
    data = extract_contacts(html, url)
    for page in data.pop("contact_pages"):
        sub = fetch(page)
        if not sub:
            continue
        more = extract_contacts(sub, page)
        for k in ("emails", "phones", "whatsapp", "linkedin"):
            data[k] = sorted(set(data[k]) | set(more[k]))
        data["text"] += " " + more["text"][:3000]
    # Prioriza correos del mismo dominio que el sitio.
    dom = domain_of(url)
    data["emails"].sort(key=lambda e: (not e.endswith(dom), e))
    return data
