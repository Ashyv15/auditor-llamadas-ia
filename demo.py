"""Demostración con las llamadas ficticias de ejemplos/.

Uso:
  python demo.py            usa los hechos ya extraídos (ejemplos/*.hechos.json); no necesita Ollama ni GPU.
  python demo.py --ollama   pide los hechos al modelo local de Ollama (AUDITOR_MODELO, por defecto qwen2.5:7b).
"""
import glob
import json
import os
import sys

from auditor.decidir import decidir
from auditor.enmascarar import enmascarar

AQUI = os.path.dirname(os.path.abspath(__file__))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Tildes en la consola de Windows.
    usar_ollama = "--ollama" in sys.argv
    for ruta in sorted(glob.glob(os.path.join(AQUI, "ejemplos", "llamada_*.txt"))):
        with open(ruta, encoding="utf-8") as f:
            texto = enmascarar(f.read())
        if usar_ollama:
            from auditor.extraer import extraer
            hechos = extraer(texto)
        else:
            with open(ruta[:-4] + ".hechos.json", encoding="utf-8") as f:
                hechos = json.load(f)
        r = decidir(texto, hechos)
        print(f"\n=== {os.path.basename(ruta)} ===")
        print("Transcripción enmascarada:")
        print("  " + texto.strip().replace("\n", "\n  "))
        print(f"Estado: {r['estado']} | reacción: {r['reaccion']} | intentos verificados: {r['intentos_verificados']}")
        for tipo, a in r["avisos"].items():
            print(f"  AVISO {a['categoria']} ({a['minuto']}, prueba: {a['prueba']}): «{a['cita']}»"
                  + (f" — {a['detalle']}" if a.get("detalle") else ""))
        for n in r["notas"]:
            print(f"  nota: {n}")


if __name__ == "__main__":
    main()
