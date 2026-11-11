"""Enmascarado de datos personales en transcripciones, antes de que nadie (persona o modelo) las lea.

Se aplica en local, sobre la transcripción recién generada. El texto original no sale del equipo; lo que se revisa y lo
que recibe el modelo es la copia enmascarada. Cubre los datos que en una llamada de venta suelen dictarse en voz alta:
documentos de identidad, cuentas bancarias, correos, teléfonos y números dictados palabra a palabra.
"""
import re

DIG = r"(?:cero|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)"

PATRONES = [
    (re.compile(r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]{2,4}){3,}\b"), "[IBAN]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\b(?:[XYZxyz][ -]?)?\d{7,8}[ -]?[A-Za-z]\b"), "[DOC]"),
    (re.compile(r"\b\d(?:[ .,-]?\d){3,}\b"), "[NUM]"),
    (re.compile(rf"\b{DIG}(?:[ ,.-]+{DIG}){{3,}}\b", re.I), "[NUM]"),
]

# Nombres propios tras fórmulas de presentación: «me llamo X», «soy X», «a nombre de X».
NOMBRE = re.compile(r"\b(me llamo|mi nombre es|soy|habla con|a nombre de|hablo con)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,3})")
NO_NOMBRE = {"El", "La", "Los", "Las", "Un", "Una", "Otra", "Otro", "Su", "Tu", "Mi", "Usted"}


def enmascarar(texto):
    """Devuelve el texto con los datos personales sustituidos por etiquetas."""
    for patron, etiqueta in PATRONES:
        texto = patron.sub(etiqueta, texto)

    def nombre(m):
        if m[2].split()[0] in NO_NOMBRE:
            return m[0]
        return f"{m[1]} [NOMBRE]"
    return NOMBRE.sub(nombre, texto)
