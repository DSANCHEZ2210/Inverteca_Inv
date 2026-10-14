"""Búsqueda web.

Sin clave prueba varios buscadores gratis en orden (DuckDuckGo, DuckDuckGo Lite, Mojeek,
Bing) y usa el primero que devuelva resultados, porque a veces bloquean a los
servidores de GitHub. Si existe la variable de entorno BRAVE_API_KEY usa Brave Search
API (plan gratis de 2,000 búsquedas al mes), que es lo más estable.
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

# Buscadores que dejaron de responder en esta corrida; no se vuelven a intentar.
_dead = set()


def search(query, limit=10):
    """Devuelve una lista de {title, url, snippet}."""
    key = os.environ.get("BRAVE_API_KEY")
    if key:
        try:
            return _brave(query, limit, key)
        except requests.RequestException as e:
            print(f"  ! Brave falló: {e}")
    for name, fn in ENGINES:
        if name in _dead:
            continue
        try:
            res = fn(query)
        except requests.RequestException as e:
            print(f"  ! {name} falló: {e}")
            res = []
        if res:
            print(f"  {name}: {len(res)} resultados")
            return res[:limit]
        print(f"  {name}: sin resultados, pruebo el siguiente")
        _dead.add(name)
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


def _get(method, url, **kw):
    r = requests.request(method, url, headers=HEADERS, timeout=20, **kw)
    r.raise_for_status()
    time.sleep(2)
    return r.text


def _duckduckgo(query):
    return parse_duckduckgo(_get("POST", "https://html.duckduckgo.com/html/", data={"q": query, "kl": "mx-es"}))


def _duckduckgo_lite(query):
    return parse_duckduckgo_lite(_get("POST", "https://lite.duckduckgo.com/lite/", data={"q": query, "kl": "mx-es"}))


def _bing(query):
    return parse_bing(_get("GET", "https://www.bing.com/search", params={"q": query, "cc": "MX", "setlang": "es"}))


def _mojeek(query):
    return parse_mojeek(_get("GET", "https://www.mojeek.com/search", params={"q": query, "lb": "es"}))


ENGINES = [
    ("DuckDuckGo", _duckduckgo),
    ("DuckDuckGo Lite", _duckduckgo_lite),
    ("Mojeek", _mojeek),
    ("Bing", _bing),
]


def parse_duckduckgo(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for res in soup.select("div.result"):
        a = res.select_one("a.result__a")
        if not a:
            continue
        snip = res.select_one(".result__snippet")
        _add(out, a.get_text(" ", strip=True), _unwrap(a.get("href", "")), snip)
    return out


def parse_duckduckgo_lite(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    links = soup.select("a.result-link")
    snippets = soup.select("td.result-snippet")
    for i, a in enumerate(links):
        _add(out, a.get_text(" ", strip=True), _unwrap(a.get("href", "")), snippets[i] if i < len(snippets) else None)
    return out


def parse_bing(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for li in soup.select("li.b_algo"):
        a = li.select_one("h2 a")
        if not a:
            continue
        _add(out, a.get_text(" ", strip=True), _unwrap_bing(a.get("href", "")), li.select_one(".b_caption p, p"))
    return out


def parse_mojeek(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for li in soup.select("ul.results-standard > li"):
        a = li.select_one("h2 a") or li.select_one("a.title") or li.select_one("a.ob")
        if not a:
            continue
        _add(out, a.get_text(" ", strip=True), a.get("href", ""), li.select_one("p.s"))
    return out


def _add(out, title, url, snippet_tag):
    if url.startswith("http"):
        out.append({"title": title, "url": url,
                    "snippet": snippet_tag.get_text(" ", strip=True) if snippet_tag else ""})


def _unwrap(href):
    # DuckDuckGo envuelve los links como //duckduckgo.com/l/?uddg=<url real>
    if "uddg=" in href:
        q = parse_qs(urlparse(href if href.startswith("http") else "https:" + href).query)
        if "uddg" in q:
            return unquote(q["uddg"][0])
    return href


def _unwrap_bing(href):
    # Bing a veces usa bing.com/ck/a?...&u=a1<base64 de la url real>
    if "bing.com/ck/a" in href:
        import base64
        u = parse_qs(urlparse(href).query).get("u", [""])[0]
        if u.startswith("a1"):
            b = u[2:] + "=" * (-len(u[2:]) % 4)
            try:
                return base64.urlsafe_b64decode(b).decode()
            except ValueError:
                pass
    return href


def _strip(text):
    return BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)
