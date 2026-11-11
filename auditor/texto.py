"""Utilidades de texto: normalizar, leer transcripciones con marca de tiempo y comprobar que una cita es literal.

La comprobación de citas es la pieza central del diseño: el modelo de lenguaje propone hechos con una frase de prueba y
el código solo los acepta si esa frase aparece en la transcripción. Si no aparece, se descarta como posible alucinación.
"""
import difflib
import re
import unicodedata

UMBRAL_CITA = 0.85        # Parecido mínimo entre la cita y el tramo de la transcripción.
UMBRAL_LITERAL = 0.98     # A partir de aquí la cita se considera literal.
MAX_PALABRAS_CITA = 150   # Una "cita" más larga no es una cita: es un resumen y no sirve como prueba.


def norm(t):
    """Minúsculas, sin tildes ni signos, espacios simples."""
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\W+", " ", t).strip()


def lineas_con_tiempo(texto):
    """Lista de (minuto, frase) de una transcripción con líneas «[mm:ss] texto»."""
    salida = []
    for linea in texto.splitlines():
        m = re.match(r"\[(\d\d:\d\d)\]\s*(.*)", linea)
        if m:
            salida.append((m[1], m[2]))
    return salida


def indexar(lineas):
    """Lista de (palabra normalizada, minuto) para ubicar citas."""
    return [(p, pos) for pos, frase in lineas for p in norm(frase).split()]


def localizar(cita, palabras):
    """Busca la cita en la transcripción. Devuelve (estado, minuto):
    ("Verificada", mm:ss) si es literal, ("Parecida", mm:ss) si se parece lo bastante, (None, None) si no aparece."""
    trozos = [norm(t) for t in re.split(r"\.\.\.|…", cita or "")]
    e = max(trozos, key=len, default="")
    n = len(e.split())
    if n < 2 or n > MAX_PALABRAS_CITA:
        return None, None
    solo = [p for p, _ in palabras]
    mejor, inicio = 0.0, None
    for i in range(0, max(1, len(solo) - n + 1)):
        tramo = " ".join(solo[i:i + n])
        sm = difflib.SequenceMatcher(None, tramo, e, autojunk=False)
        if sm.quick_ratio() >= UMBRAL_CITA:
            r = sm.ratio()
            if r > mejor:
                mejor, inicio = r, i
    if inicio is None or mejor < UMBRAL_CITA:
        return None, None
    return ("Verificada" if mejor >= UMBRAL_LITERAL else "Parecida"), palabras[inicio][1]
