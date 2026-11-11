"""Extracción de hechos con un modelo de lenguaje local (Ollama). El modelo no decide si hay falta: solo responde a
preguntas concretas sobre la llamada y aporta, para cada respuesta, la frase literal que la prueba.

La respuesta se fuerza a un esquema JSON (salida estructurada de Ollama) y temperatura 0 para que sea repetible.
Todo ocurre en local: la transcripción enmascarada se envía a 127.0.0.1, nunca a un servicio externo.
"""
import json
import os
import urllib.request

URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODELO = os.environ.get("AUDITOR_MODELO", "qwen2.5:7b")
NUM_CTX = 16384

ALERTAS = ["promesa", "datos_de_tercero", "comunicacion_externa"]

PROPIEDADES = {
    "tipo_llamada": {"enum": ["venta", "seguimiento", "sin_conversacion"]},
    "oferta": {"type": "string"},
    "cita_rechazo": {"type": "string"},
    "reaccion": {"enum": ["insiste", "se_rinde", "cliente_cuelga", "sin_rechazo"]},
    "intentos": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
    "pide_no_llamar": {"type": "string"},
    "alertas": {"type": "object", "required": ALERTAS, "properties": {t: {"type": "string"} for t in ALERTAS}},
    "resumen": {"type": "string"},
}
ESQUEMA = {"type": "object", "required": list(PROPIEDADES), "properties": PROPIEDADES}

SISTEMA = """Eres un analista de calidad de llamadas de venta. Responde SOLO con hechos de la transcripción.
Reglas:
- Cada campo de texto es una cita LITERAL y corta (una o dos frases) copiada de la transcripción, o vacío si no ocurre.
- No resumas dentro de una cita ni unas frases de minutos distintos.
- oferta: la frase donde el asesor da un precio o un producto concreto.
- cita_rechazo: la primera frase en la que el cliente rechaza la propuesta.
- reaccion: qué hace el asesor tras ese rechazo. intentos: frases del asesor que argumentan después del rechazo.
- pide_no_llamar: frase del cliente pidiendo que no le llamen más.
- alertas.promesa: el asesor promete algo que no forma parte de la oferta (descuentos futuros, regalos no incluidos).
  Un precio fijo o promocional NO es una promesa.
- alertas.datos_de_tercero: el asesor propone tramitar a nombre de alguien que no está en la llamada o pide su documento.
- alertas.comunicacion_externa: el asesor propone seguir por un canal personal (su WhatsApp, su número).
- resumen: dos frases, sin nombres ni datos personales."""


def extraer(transcripcion_enmascarada):
    """Pregunta al modelo local y devuelve el diccionario de hechos."""
    cuerpo = json.dumps({
        "model": MODELO, "stream": False, "format": ESQUEMA,
        "options": {"num_ctx": NUM_CTX, "temperature": 0},
        "messages": [{"role": "system", "content": SISTEMA},
                     {"role": "user", "content": "TRANSCRIPCIÓN:\n" + transcripcion_enmascarada}],
    }).encode()
    peticion = urllib.request.Request(URL + "/api/chat", cuerpo, {"Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=3600) as r:
        return json.loads(json.load(r)["message"]["content"])
