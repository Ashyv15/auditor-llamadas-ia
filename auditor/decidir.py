"""Decisión por reglas a partir de los hechos del modelo y de la propia transcripción.

Principios:
1. Sin prueba no hay aviso: cada hecho del modelo se acepta solo si su cita aparece en la transcripción (localizar).
2. Doble vía: las faltas graves se buscan también con reglas sobre el texto, por si el modelo no las ve.
3. El sistema no sanciona. Propone casos «por validar» con la frase y el minuto; una persona escucha y decide.
"""
import re

from .texto import indexar, lineas_con_tiempo, localizar, norm

MIN_INTENTOS = 2  # Intentos verificados tras el rechazo para considerar que el asesor insistió.

# Tramitar a nombre de otra persona (regla de respaldo, independiente del modelo).
A_NOMBRE_DE_OTRO = (r"\b(a|al|en) nombre de (otra persona|otro titular|un familiar|algun familiar|tu (marido|mujer|pareja|hermano|hermana|madre|padre)|su (marido|mujer|pareja))\b"
                    r"|\botr[oa] (dni|nie|documento)\b|\b(dni|documento) de (tu|su) (marido|mujer|pareja|hermano|hermana|madre|padre)\b")
# Frases que hablan de ello para desaconsejarlo: no cuentan.
A_NOMBRE_NEGADO = (r"\bnombre de (otra persona|otro|otra)\b.{0,20}\bno (te|le)? ?(da|sirve|conviene)\b"
                   r"|\bno (se )?(puede|podemos) (poner|tramitar)\w* a nombre de\b")
NO_LLAMAR = r"\b(no me (llam\w+|volvais a llamar|vuelvas a llamar)( mas)?|lista robinson|dejad de llamar(me)?|borr\w+ mi numero)\b"
PRECIO_PERMITIDO = r"\b(precio (fijo|para siempre)|sin subidas|tarifa fija)\b"

CATEGORIA = {
    "datos_de_tercero": "Grave: datos de terceros",
    "comunicacion_externa": "Grave: comunicación fuera de los canales oficiales",
    "promesa": "Moderada: falsas expectativas",
    "se_rinde": "Moderada: abandona tras el primer rechazo",
    "no_llamar": "Revisar: el cliente pide no ser llamado",
}


def _con_prueba(cita, palabras):
    estado, minuto = localizar(cita, palabras)
    return (estado, minuto) if estado else (None, None)


def decidir(transcripcion, hechos):
    """Devuelve el resultado de la llamada: estado, avisos por validar (con cita y minuto) y notas de lo descartado."""
    lineas = lineas_con_tiempo(transcripcion)
    palabras = indexar(lineas)
    avisos, notas = {}, []

    def aviso(tipo, cita, minuto, estado, detalle=""):
        avisos[tipo] = {"categoria": CATEGORIA[tipo], "cita": cita, "minuto": minuto, "prueba": estado,
                        "estado": "Por validar", **({"detalle": detalle} if detalle else {})}

    # 1. Alertas del modelo: solo con cita localizada.
    for tipo, cita in (hechos.get("alertas") or {}).items():
        if not (cita or "").strip():
            continue
        estado, minuto = _con_prueba(cita, palabras)
        if not estado:
            notas.append(f"{tipo}: la cita del modelo no aparece en la transcripción; descartada como posible alucinación")
            continue
        if tipo == "promesa" and re.search(PRECIO_PERMITIDO, norm(cita)):
            notas.append("promesa: es un precio fijo o promocional, permitido; descartada")
            continue
        aviso(tipo, cita, minuto, estado)

    # 2. Regla de respaldo para datos de terceros, aunque el modelo no lo vea.
    if "datos_de_tercero" not in avisos:
        for minuto, frase in lineas:
            n = norm(frase)
            if re.search(A_NOMBRE_DE_OTRO, n) and not re.search(A_NOMBRE_NEGADO, n):
                aviso("datos_de_tercero", frase, minuto, "Regla", "detectado por regla sin alerta del modelo")
                break

    # 3. El cliente pide no ser llamado (regla sobre el texto).
    for minuto, frase in lineas:
        if re.search(NO_LLAMAR, norm(frase)):
            aviso("no_llamar", frase, minuto, "Regla")
            break

    # 4. Reacción ante el rechazo: el modelo propone, los intentos verificados deciden.
    reaccion = hechos.get("reaccion")
    rechazo_estado, rechazo_min = _con_prueba(hechos.get("cita_rechazo"), palabras)
    intentos = [(c, m) for c in hechos.get("intentos") or [] for e, m in [_con_prueba(c, palabras)] if e]
    if rechazo_min:
        intentos = [(c, m) for c, m in intentos if m >= rechazo_min]
    if reaccion == "se_rinde":
        if len(intentos) >= MIN_INTENTOS:
            notas.append(f"el modelo dice que se rinde, pero hay {len(intentos)} intentos verificados tras el rechazo: insiste")
            reaccion = "insiste"
        elif not rechazo_estado:
            notas.append("el modelo dice que se rinde, pero la cita del rechazo no aparece: no se acusa")
            reaccion = "dudoso"
        else:
            aviso("se_rinde", hechos["cita_rechazo"], rechazo_min, rechazo_estado,
                  f"{len(intentos)} intento(s) verificado(s) tras el rechazo")

    if hechos.get("tipo_llamada") == "sin_conversacion":
        estado = "no_evaluable"
    elif avisos:
        estado = "por_validar"
    else:
        estado = "sin_avisos"
    return {"estado": estado, "reaccion": reaccion, "intentos_verificados": len(intentos),
            "avisos": avisos, "notas": notas, "resumen": hechos.get("resumen", "")}
