"""Búsqueda web.

Por defecto usa DuckDuckGo (gratis, sin clave). Si existe la variable de entorno
BRAVE_API_KEY usa Brave Search API (plan gratis de 2,000 búsquedas al mes), que es
más estable desde los servidores de GitHub.
"""
import os
import time
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}


def search(query, limit=10):
    """Devuelve una lista de {title, url, snippet}."""
    key = os.environ.get("BRAVE_API_KEY")
    try:
        if key:
            return _brave(query, limit, key)
        return _duckduckgo(query, limit)
    except requests.RequestException as e:
        print(f"  ! búsqueda falló ({query}): {e}")
        return []


def _brave(query, limit, key):
    r = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": min(limit, 20), "country": "mx", "search_lang": "es"},
        headers={"X-Subscription-Token": key, "Accept": "application/json"},
        timeout=20,
    )
    r.raise_for_status()
    time.sleep(1.1)  # el plan gratis permite 1 consulta por segundo
    return [
        {"title": x.get("title", ""), "url": x.get("url", ""), "snippet": _strip(x.get("description", ""))}
        for x in r.json().get("web", {}).get("results", [])
    ][:limit]


def _duckduckgo(query, limit):
    r = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query, "kl": "mx-es"},
        headers=HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    time.sleep(2)
    return parse_duckduckgo(r.text)[:limit]


def parse_duckduckgo(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for res in soup.select("div.result"):
        a = res.select_one("a.result__a")
        if not a:
            continue
        url = _unwrap(a.get("href", ""))
        if not url.startswith("http"):
            continue
        snip = res.select_one(".result__snippet")
        out.append({
            "title": a.get_text(" ", strip=True),
            "url": url,
            "snippet": snip.get_text(" ", strip=True) if snip else "",
        })
    return out


def _unwrap(href):
    # DuckDuckGo envuelve los links como //duckduckgo.com/l/?uddg=<url real>
    if "uddg=" in href:
        q = parse_qs(urlparse(href if href.startswith("http") else "https:" + href).query)
        if "uddg" in q:
            return unquote(q["uddg"][0])
    return href


def _strip(text):
    return BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)
