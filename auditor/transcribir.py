"""Transcripción local con faster-whisper (CPU). Guarda dos ficheros por audio:
- <audio>.txt: transcripción original, que no sale del equipo y no se revisa.
- <audio>.enmascarado.txt: la copia con datos personales enmascarados, la única que leen personas y el modelo.
"""
import os

from .enmascarar import enmascarar

MODELO_WHISPER = os.environ.get("AUDITOR_WHISPER", "large-v3-turbo")


def mmss(s):
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


def transcribir(ruta_audio, carpeta_salida, idioma="es"):
    from faster_whisper import WhisperModel  # Import tardío: el resto del proyecto funciona sin instalarlo.
    modelo = WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")
    segmentos, _ = modelo.transcribe(ruta_audio, language=idioma, vad_filter=True)
    texto = "\n".join(f"[{mmss(s.start)}] {s.text.strip()}" for s in segmentos)
    os.makedirs(carpeta_salida, exist_ok=True)
    base = os.path.join(carpeta_salida, os.path.splitext(os.path.basename(ruta_audio))[0])
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(texto)
    with open(base + ".enmascarado.txt", "w", encoding="utf-8") as f:
        f.write(enmascarar(texto))
    return base + ".enmascarado.txt"
