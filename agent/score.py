"""Clasificación y puntaje de probabilidad de inversión (0 a 100)."""
from . import config


def classify(text):
    t = text.lower()
    for kind, words in config.TYPE_KEYWORDS.items():
        if any(w in t for w in words):
            return kind
    return "Otro"


def score(prospect):
    """Devuelve (puntaje, razones). El texto analizado es título + snippet + contenido del sitio."""
    t = " ".join([
        prospect.get("name", ""), prospect.get("snippet", ""),
        prospect.get("description", ""), prospect.get("text", ""),
    ]).lower()
    points, reasons = 0, []

    tp = config.TYPE_POINTS.get(prospect.get("type", "Otro"), 0)
    if tp:
        points += tp
        reasons.append(prospect["type"])

    labels = {
        "real_estate": "Invierte en bienes raíces",
        "nuevo_leon": "Está en Nuevo León",
        "mexico": "Opera en México",
        "income": "Busca flujo / rendimiento",
        "alternatives": "Abierto a alternativas",
    }
    for key, (words, pts) in config.SCORING.items():
        if key == "mexico" and "Está en Nuevo León" in reasons:
            continue
        if any(w in t for w in words):
            points += pts
            reasons.append(labels[key])

    contact = 0
    if prospect.get("emails"):
        contact += config.CONTACT_POINTS["email"]
    if prospect.get("phones"):
        contact += config.CONTACT_POINTS["phone"]
    if prospect.get("whatsapp"):
        contact += config.CONTACT_POINTS["whatsapp"]
    if prospect.get("linkedin"):
        contact += config.CONTACT_POINTS["linkedin"]
    if contact:
        points += contact
        reasons.append("Tiene contacto directo")
    else:
        points -= 15  # sin forma de contactar no sirve para el top

    max_points = (max(config.TYPE_POINTS.values()) + sum(p for k, (_, p) in config.SCORING.items() if k != "mexico")
                  + sum(config.CONTACT_POINTS.values()))
    return max(0, min(100, round(points * 100 / max_points))), reasons
