"""Configuración del agente: qué buscar y cómo puntuar.

Edita estas listas para cambiar el enfoque de la búsqueda sin tocar el resto del código.
"""

# Búsquedas que el agente lanza cada día. Se rotan para no repetir siempre las mismas.
QUERIES = [
    # Family offices
    "family office Monterrey",
    "family office México inversión inmobiliaria",
    "family office Guadalajara inversiones",
    "family office Ciudad de México real estate",
    "multi family office México",
    # Fondos e instituciones
    "fondo de inversión inmobiliario México",
    "fondo de capital privado bienes raíces México",
    "private equity real estate Mexico fund",
    "gestora de fondos inmobiliarios Nuevo León",
    "CKD inmobiliario administrador México",
    "fondo de inversión Monterrey contacto",
    "socios AMEXCAP real estate",
    # Personas físicas con perfil público de inversionista
    "inversionista ángel Monterrey",
    "inversionista ángel México bienes raíces",
    "red de inversionistas ángeles México",
    "inversionista inmobiliario Monterrey contacto",
    "club de inversionistas Monterrey",
    "asesor patrimonial independiente Monterrey",
    "wealth management Monterrey",
]

# Cuántas búsquedas por corrida (las demás se usan en los días siguientes).
QUERIES_PER_RUN = 8
RESULTS_PER_QUERY = 10

# Dominios que no son prospectos (redes sociales, medios, directorios genéricos, etc.).
BLOCKED_DOMAINS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com", "tiktok.com",
    "wikipedia.org", "google.com", "bing.com", "duckduckgo.com", "amazon.com",
    "indeed.com", "glassdoor.com", "occ.com.mx", "computrabajo.com", "reddit.com",
    "forbes.com.mx", "expansion.mx", "elfinanciero.com.mx", "eleconomista.com.mx",
    "elnorte.com", "milenio.com", "infobae.com", "bloomberg.com", "reuters.com",
    "inverteca.mx", "pinterest.com", "scribd.com", "issuu.com", "medium.com",
    "gob.mx", "cnbv.gob.mx", "finance.yahoo.com", "investing.com", "marketwatch.com",
    "stockanalysis.com", "zacks.com", "britannica.com", "rae.es", "pexels.com", "pixabay.com",
    "stackexchange.com", "microsoft.com", "familysearch.org", "condusef.gob.mx", "mercadolibre.com.mx",
}

# Filtro de relevancia: un sitio solo entra a la base si su texto tiene al menos una
# palabra de inversión Y alguna señal de México. Así se descarta la basura del buscador.
RELEVANCE_INVEST = [
    "family office", "oficina familiar", "fondo de inversión", "fondos de inversión", "private equity",
    "capital privado", "venture capital", "capital de riesgo", "inversionista", "inversor",
    "angel investor", "inversión inmobiliaria", "inversiones inmobiliarias", "real estate investment",
    "gestión patrimonial", "wealth management", "banca privada", "asset management",
    "administradora de fondos", "gestora", "ckd", "cerpi", "fibra", "portafolio de inversión",
    "patrimonio familiar", "investment", "inversiones",
]
RELEVANCE_MEXICO = [
    "méxico", "mexico", "monterrey", "nuevo león", "nuevo leon", "cdmx", "ciudad de méxico",
    "guadalajara", "jalisco", "querétaro", "queretaro", "san pedro garza", "+52", "mxn",
]
# Sitios que no son prospectos aunque mencionen inversión.
RELEVANCE_BLOCK_WORDS = [
    "diccionario", "dictionary", "fondos de pantalla", "wallpaper", "grammar", "stock quote",
    "cotización de la acción", "market report", "market size",
]

# Palabras para clasificar el tipo de prospecto (se busca en título + snippet + web).
TYPE_KEYWORDS = {
    "Family office": ["family office", "familiy office", "oficina familiar", "multi family", "multifamily office"],
    "Fondo de inversión": [
        "fondo de inversión", "fondo de capital", "private equity", "capital privado",
        "venture capital", "gestora", "asset management", "administradora de fondos",
        "ckd", "cerpi", "fund", "fondos",
    ],
    "Asesor patrimonial": ["wealth management", "asesor patrimonial", "banca privada", "gestión patrimonial", "asesoría patrimonial"],
    "Persona física": ["inversionista ángel", "angel investor", "inversionista", "business angel"],
}

# Señales que suben la probabilidad de inversión en Inverteca.
SCORING = {
    # (palabras, puntos)
    "real_estate": (["inmobiliari", "bienes raíces", "bienes raices", "real estate", "propiedades",
                     "rentas", "naves industriales", "bodegas", "industrial", "fibra", "plusvalía"], 30),
    "nuevo_leon": (["monterrey", "nuevo león", "nuevo leon", "san pedro garza", "san pedro", "n.l."], 20),
    "mexico": (["méxico", "mexico", "cdmx", "guadalajara", "querétaro", "queretaro", "jalisco"], 10),
    "income": (["flujo", "renta fija", "ingresos pasivos", "income", "dividendos", "rendimiento"], 10),
    "alternatives": (["alternativ", "diversific", "crowdfunding", "fintech", "coinversión", "coinversion"], 10),
}

# Puntos por tipo: quién es más probable que invierta rápido.
TYPE_POINTS = {
    "Family office": 25,
    "Persona física": 20,
    "Asesor patrimonial": 15,
    "Fondo de inversión": 15,
    "Otro": 0,
}

# Puntos por tener forma de contactar.
CONTACT_POINTS = {"email": 10, "phone": 8, "whatsapp": 5, "linkedin": 3}

TOP_N = 5
