# Prospectos Inverteca

Agente que busca cada día family offices, fondos de inversión, asesores patrimoniales y personas
con perfil de inversionista en México, saca sus datos de contacto públicos, les da un puntaje de
probabilidad de invertir en Inverteca y publica el top 5 en una página protegida con contraseña.

## Cómo funciona

1. **Busca** (`agent/search.py`): lanza 8 búsquedas al día (lista en `agent/config.py`), rotando para cubrir todas.
2. **Visita** (`agent/extract.py`): entra al sitio de cada resultado nuevo y a su página de contacto y saca
   correos, teléfonos, WhatsApp y LinkedIn publicados. LinkedIn nunca se raspa: solo se guarda el link del perfil.
3. **Puntúa** (`agent/score.py`): tipo de prospecto + invierte en bienes raíces + está en Nuevo León/México +
   busca flujo + tiene forma de contactarlo. Los pesos se cambian en `agent/config.py`.
4. **Publica** (`docs/`): la base se guarda cifrada (AES-256) en `docs/data.enc.json`; la página la abre en el
   navegador con la contraseña. Aunque el repositorio y la página sean públicos, sin contraseña no se ve nada.

GitHub Actions (`.github/workflows/actualizar.yml`) lo corre todos los días a las 6:00 am de Monterrey.

## Puesta en marcha (una sola vez)

1. **Contraseña:** Settings → Secrets and variables → Actions → New repository secret →
   nombre `SITE_PASSWORD`, valor la contraseña que usarán tú y tu jefe.
2. **Página:** Settings → Pages → Source: *Deploy from a branch* → Branch `main`, carpeta `/docs`.
3. **Primera corrida:** Actions → *Actualizar prospectos* → *Run workflow*.
4. El link queda en `https://<usuario>.github.io/<repositorio>/`.

### Opcional: búsqueda más estable

DuckDuckGo a veces bloquea los servidores de GitHub. Si las corridas traen 0 resultados, crea una clave gratis
en <https://brave.com/search/api/> (plan Free, 2,000 búsquedas al mes) y guárdala como secret `BRAVE_API_KEY`.

## Agregar prospectos a mano

Agrega filas a `seeds.csv` (`nombre,url,tipo,email,telefono,notas`). El agente las visita y las puntúa.
Ojo: este archivo no está cifrado, así que si el repositorio es público no pongas ahí correos ni teléfonos.

## Pruebas

```
pip install -r requirements.txt
python -m unittest -v
```

## Datos personales

Solo se recopilan datos publicados por el propio prospecto (su sitio web o perfil público). Antes de usarlos
para contacto comercial, revisen que cumplan con la LFPDPPP y el aviso de privacidad de Inverteca.
