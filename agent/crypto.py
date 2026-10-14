"""Cifra la base para que la página pública solo se lea con contraseña.

Formato compatible con Web Crypto del navegador: PBKDF2-SHA256 + AES-256-GCM.
"""
import base64
import json
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITERATIONS = 250_000


def _key(password, salt):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return kdf.derive(password.encode())


def encrypt(obj, password):
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_key(password, salt)).encrypt(iv, json.dumps(obj, ensure_ascii=False).encode(), None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "iter": ITERATIONS, "salt": b64(salt), "iv": b64(iv), "data": b64(ct)}


def decrypt(blob, password):
    d = lambda k: base64.b64decode(blob[k])
    pt = AESGCM(_key(password, d("salt"))).decrypt(d("iv"), d("data"), None)
    return json.loads(pt)
