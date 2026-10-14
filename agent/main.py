"""Corrida diaria del agente.

1. Lanza las búsquedas del día.
2. Visita cada sitio nuevo y saca contactos públicos.
3. Clasifica y puntúa.
4. Junta todo con la base anterior y la guarda cifrada en docs/data.enc.json.

Uso:  SITE_PASSWORD=... python -m agent.main
"""
import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

from . import config
from .crypto import decrypt, encrypt
from .extract import domain_of, enrich
from .score import classify, score
from .search import search

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "docs" / "data.enc.json"
SEEDS_FILE = ROOT / "seeds.csv"
MAX_NEW_SITES = int(os.environ.get("MAX_NEW_SITES", "40"))


def todays_queries(today):
    n = len(config.QUERIES)
    start = (today.toordinal() * config.QUERIES_PER_RUN) % n
    return [config.QUERIES[(start + i) % n] for i in range(min(config.QUERIES_PER_RUN, n))]


def key_for(url):
    if "linkedin.com/in/" in url:
        return url.split("?")[0].rstrip("/").lower()
    return domain_of(url)


def is_blocked(url):
    dom = domain_of(url)
    if "linkedin.com" in dom:
        return "/in/" not in url and "/company/" not in url
    return any(dom == b or dom.endswith("." + b) for b in config.BLOCKED_DOMAINS)


def clean_name(title):
    for sep in (" | ", " - ", " – ", " — ", ": "):
        if sep in title:
            title = title.split(sep)[0]
    return title.strip()[:90]


def load_db(password):
    if not DATA_FILE.exists():
        return {}
    blob = json.loads(DATA_FILE.read_text())
    return {p["key"]: p for p in decrypt(blob, password)["prospects"]}


def load_seeds():
    if not SEEDS_FILE.exists():
        return []
    with SEEDS_FILE.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("url") or "").strip() and not r["url"].startswith("#")]
    return [{"title": r.get("nombre", ""), "url": r["url"].strip(), "snippet": r.get("notas", ""),
             "seed": r} for r in rows]


def build_prospect(hit, today):
    url = hit["url"]
    p = {
        "key": key_for(url),
        "name": clean_name(hit.get("title", "")) or domain_of(url),
        "url": url,
        "snippet": hit.get("snippet", ""),
        "query": hit.get("query", "semilla"),
        "emails": [], "phones": [], "whatsapp": [], "linkedin": [],
        "first_seen": today, "last_seen": today,
    }
    if "linkedin.com/" in url:
        # Nunca raspamos LinkedIn: solo guardamos el perfil que salió en la búsqueda.
        p["linkedin"] = [url.split("?")[0]]
        p["description"] = ""
        p["text"] = ""
    else:
        site = enrich(url)
        if site is None:
            return None
        for k in ("emails", "phones", "whatsapp", "linkedin"):
            p[k] = site[k][:5]
        p["description"] = site["description"][:300]
        p["text"] = site["text"]
        if site["title"] and len(clean_name(site["title"])) > 2 and not hit.get("seed"):
            p["name"] = clean_name(site["title"])

    seed = hit.get("seed") or {}
    if seed.get("email"):
        p["emails"] = [seed["email"].strip()] + p["emails"]
    if seed.get("telefono"):
        p["phones"] = [seed["telefono"].strip()] + p["phones"]
    kind = (seed.get("tipo") or "").strip()
    if not kind and "linkedin.com/in/" in url:
        kind = "Persona física"
    if not kind:
        # Primero por lo que dice el propio prospecto; la búsqueda que lo encontró solo desempata.
        kind = classify(" ".join([p["name"], p["snippet"], p["description"], p["text"][:2000]]))
        if kind == "Otro":
            kind = classify(hit.get("query", ""))
    p["type"] = kind
    return p


def run():
    password = os.environ.get("SITE_PASSWORD")
    if not password:
        sys.exit("Falta la variable SITE_PASSWORD")
    today_d = dt.date.today()
    today = today_d.isoformat()
    db = load_db(password)

    hits = load_seeds()
    for q in todays_queries(today_d):
        print(f"Buscando: {q}")
        for h in search(q, config.RESULTS_PER_QUERY):
            h["query"] = q
            hits.append(h)

    added = 0
    for h in hits:
        url = h["url"]
        if is_blocked(url):
            continue
        k = key_for(url)
        if k in db:
            db[k]["last_seen"] = today
            continue
        if added >= MAX_NEW_SITES:
            continue
        print(f"  visitando {url}")
        p = build_prospect(h, today)
        if p:
            db[k] = p
            added += 1

    for p in db.values():
        p["score"], p["reasons"] = score(p)

    prospects = sorted(db.values(), key=lambda p: p["score"], reverse=True)
    # El texto del sitio solo sirve para volver a puntuar; guardamos un recorte para que el archivo sea ligero.
    for p in prospects:
        p["text"] = p.get("text", "")[:1500]
    out = {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
        "new_today": added,
        "top_n": config.TOP_N,
        "prospects": prospects,
    }
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(encrypt(out, password)))
    print(f"Listo: {added} nuevos, {len(prospects)} en total.")


if __name__ == "__main__":
    run()
