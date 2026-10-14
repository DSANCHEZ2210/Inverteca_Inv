"""Pruebas sin internet: simulan buscador y sitios web."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent import crypto, extract, main, score, search

DDG_HTML = """
<div class="result"><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.fo-ejemplo.mx%2F&rut=x">
FO Ejemplo | Family Office en Monterrey</a><a class="result__snippet">Family office en San Pedro que invierte en bienes raíces.</a></div>
<div class="result"><a class="result__a" href="https://www.facebook.com/algo">Facebook</a></div>
<div class="result"><a class="result__a" href="https://mx.linkedin.com/in/juan-perez-123">Juan Pérez - Inversionista ángel - Monterrey | LinkedIn</a>
<a class="result__snippet">Inversionista ángel en real estate, Monterrey.</a></div>
"""

SITE_HOME = """<html><head><title>FO Ejemplo - Inicio</title>
<meta name="description" content="Family office regiomontano enfocado en inmobiliario y rentas."></head>
<body><a href="/contacto">Contacto</a><p>Oficinas en Monterrey, Nuevo León.</p></body></html>"""
SITE_CONTACT = """<html><body><a href="mailto:hola@fo-ejemplo.mx">Escríbenos</a>
<p>Tel. (81) 8123-4567</p><a href="https://wa.me/528112345678">WhatsApp</a>
<a href="https://www.linkedin.com/company/fo-ejemplo/">LinkedIn</a>
<img src="logo@2x.png"> foo@sentry.io</body></html>"""


def fake_fetch(url, timeout=15):
    if url.rstrip("/").endswith("contacto"):
        return SITE_CONTACT
    if "fo-ejemplo.mx" in url:
        return SITE_HOME
    return None


class TestParsing(unittest.TestCase):
    def test_duckduckgo(self):
        res = search.parse_duckduckgo(DDG_HTML)
        self.assertEqual(res[0]["url"], "https://www.fo-ejemplo.mx/")
        self.assertIn("San Pedro", res[0]["snippet"])
        self.assertEqual(len(res), 3)

    def test_other_engines(self):
        lite = '<a class="result-link" href="https://fo.mx/">FO</a><td class="result-snippet">family office</td>'
        self.assertEqual(search.parse_duckduckgo_lite(lite)[0]["url"], "https://fo.mx/")
        import base64
        enc = base64.urlsafe_b64encode(b"https://fondo.mx/").decode().rstrip("=")
        bing = f'<li class="b_algo"><h2><a href="https://www.bing.com/ck/a?!&u=a1{enc}&ntb=1">Fondo</a></h2><div class="b_caption"><p>Fondo inmobiliario</p></div></li>'
        self.assertEqual(search.parse_bing(bing)[0], {"title": "Fondo", "url": "https://fondo.mx/", "snippet": "Fondo inmobiliario"})
        moj = '<ul class="results-standard"><li><h2><a class="title" href="https://x.mx/">X</a></h2><p class="s">snip</p></li></ul>'
        self.assertEqual(search.parse_mojeek(moj)[0]["url"], "https://x.mx/")

    def test_fallback(self):
        search._dead.clear()
        with mock.patch.object(search, "ENGINES", [("A", lambda q: []), ("B", lambda q: [{"title": "t", "url": "https://b.mx", "snippet": ""}])]), \
             mock.patch.dict("os.environ", {}, clear=False):
            os_key = __import__("os").environ.pop("BRAVE_API_KEY", None)
            self.assertEqual(search.search("q")[0]["url"], "https://b.mx")
            self.assertIn("A", search._dead)
        search._dead.clear()

    def test_contacts(self):
        c = extract.extract_contacts(SITE_CONTACT, "https://www.fo-ejemplo.mx/contacto")
        self.assertEqual(c["emails"], ["hola@fo-ejemplo.mx"])
        self.assertIn("+52 81 8123 4567", c["phones"])
        self.assertEqual(c["whatsapp"], ["+52 81 1234 5678"])
        self.assertEqual(c["linkedin"], ["https://www.linkedin.com/company/fo-ejemplo/"])

    def test_phone_normalize(self):
        self.assertEqual(extract.normalize_phone("+52 1 81 1234 5678"), "+52 81 1234 5678")
        self.assertIsNone(extract.normalize_phone("2024"))
        self.assertIsNone(extract.normalize_phone("0000000000"))

    def test_score(self):
        p = {"name": "FO", "type": "Family office", "text": "bienes raíces en Monterrey, rentas",
             "emails": ["a@b.mx"], "phones": ["+52 81 1111 2222"]}
        s, reasons = score.score(p)
        self.assertGreater(s, 70)
        self.assertIn("Está en Nuevo León", reasons)
        empty, _ = score.score({"name": "x", "type": "Otro"})
        self.assertEqual(empty, 0)

    def test_relevance(self):
        self.assertTrue(score.is_relevant({"url": "https://fo.mx/", "name": "FO", "text": "family office"}))
        self.assertTrue(score.is_relevant({"url": "https://fo.com/", "text": "Fondo de inversión con oficinas en Monterrey"}))
        self.assertFalse(score.is_relevant({"url": "https://dle.rae.es/fondo", "text": "Diccionario: fondo, inversión, México"}))
        self.assertFalse(score.is_relevant({"url": "https://pixabay.com/x", "text": "fotos gratis de fondos"}))

    def test_blocks_articles_and_consultancies(self):
        self.assertTrue(main.is_blocked("https://gs.com.mx/blog/family-office-inversion/"))
        self.assertTrue(main.is_blocked("https://www.ey.com/es_mx/services/family-office"))
        self.assertTrue(main.is_blocked("https://realestatemarket.com.mx/articulos/x"))
        self.assertFalse(main.is_blocked("https://www.proeza.com.mx/family-office"))
        self.assertFalse(main.is_blocked("https://mx.linkedin.com/company/ennea-family-office"))

    def test_crypto_roundtrip(self):
        blob = crypto.encrypt({"a": "ñ"}, "clave")
        self.assertEqual(crypto.decrypt(blob, "clave"), {"a": "ñ"})
        with self.assertRaises(Exception):
            crypto.decrypt(blob, "otra")


class TestRun(unittest.TestCase):
    def test_full_run_and_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data.enc.json"
            with mock.patch.object(main, "DATA_FILE", data), \
                 mock.patch.object(main, "SEEDS_FILE", Path(tmp) / "none.csv"), \
                 mock.patch.object(main, "search", lambda q, n: search.parse_duckduckgo(DDG_HTML)), \
                 mock.patch.object(extract, "fetch", fake_fetch), \
                 mock.patch.dict("os.environ", {"SITE_PASSWORD": "secreto"}):
                main.run()
                out = crypto.decrypt(json.loads(data.read_text()), "secreto")
                keys = [p["key"] for p in out["prospects"]]
                self.assertEqual(sorted(keys), ["fo-ejemplo.mx", "https://mx.linkedin.com/in/juan-perez-123"])
                fo = out["prospects"][0]
                self.assertEqual(fo["key"], "fo-ejemplo.mx")
                self.assertEqual(fo["type"], "Family office")
                self.assertEqual(fo["emails"], ["hola@fo-ejemplo.mx"])
                juan = out["prospects"][1]
                self.assertEqual(juan["type"], "Persona física")
                self.assertEqual(juan["name"], "Juan Pérez")
                # Segunda corrida: no duplica.
                main.run()
                out2 = crypto.decrypt(json.loads(data.read_text()), "secreto")
                self.assertEqual(len(out2["prospects"]), 2)
                self.assertEqual(out2["new_today"], 0)
                # Basura que entró antes del filtro se limpia en la siguiente corrida.
                junk = dict(fo, key="pixabay.com", url="https://pixabay.com/", name="Pixabay", text="fondos de pantalla")
                out2["prospects"].append(junk)
                data.write_text(json.dumps(crypto.encrypt(out2, "secreto")))
                main.run()
                out3 = crypto.decrypt(json.loads(data.read_text()), "secreto")
                self.assertNotIn("pixabay.com", [p["key"] for p in out3["prospects"]])


if __name__ == "__main__":
    unittest.main()
