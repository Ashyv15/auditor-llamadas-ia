"""Pruebas sin modelo: python -m unittest discover tests"""
import json
import os
import unittest

from auditor.decidir import decidir
from auditor.enmascarar import enmascarar
from auditor.texto import indexar, lineas_con_tiempo, localizar

EJ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ejemplos")


def ejemplo(nombre):
    with open(os.path.join(EJ, nombre + ".txt"), encoding="utf-8") as f:
        texto = enmascarar(f.read())
    with open(os.path.join(EJ, nombre + ".hechos.json"), encoding="utf-8") as f:
        return texto, json.load(f)


class Enmascarado(unittest.TestCase):
    def test_documento_correo_y_numeros(self):
        t = enmascarar("Mi DNI es 12345678Z, correo pepe@example.com, teléfono 612 345 678 y X1234567L")
        for dato in ("12345678Z", "pepe@example.com", "612 345 678", "X1234567L"):
            self.assertNotIn(dato, t)
        self.assertIn("[DOC]", t)
        self.assertIn("[EMAIL]", t)

    def test_numeros_dictados_y_iban(self):
        t = enmascarar("es el seis uno dos tres cuatro cinco y la cuenta ES91 2100 0418 4502 0005 1332")
        self.assertNotIn("seis uno dos tres", t)
        self.assertNotIn("2100 0418", t)

    def test_nombres_tras_presentacion(self):
        self.assertEqual(enmascarar("Hola, me llamo Andrés García."), "Hola, me llamo [NOMBRE].")
        self.assertEqual(enmascarar("a nombre de otra persona"), "a nombre de otra persona")


class Citas(unittest.TestCase):
    def setUp(self):
        self.p = indexar(lineas_con_tiempo("[00:10] No me interesa, gracias.\n[00:15] Vale, que tenga buena tarde."))

    def test_cita_literal(self):
        self.assertEqual(localizar("no me interesa gracias", self.p), ("Verificada", "00:10"))

    def test_cita_inventada(self):
        self.assertEqual(localizar("te escribo por mi WhatsApp personal", self.p), (None, None))


class Decision(unittest.TestCase):
    def test_se_rinde_queda_por_validar(self):
        r = decidir(*ejemplo("llamada_1_se_rinde"))
        self.assertEqual(r["estado"], "por_validar")
        self.assertEqual(r["avisos"]["se_rinde"]["minuto"], "00:15")

    def test_intentos_verificados_corrigen_al_modelo(self):
        r = decidir(*ejemplo("llamada_2_insiste"))
        self.assertEqual(r["reaccion"], "insiste")
        self.assertEqual(r["avisos"], {})

    def test_tercero_por_regla_y_alucinacion_descartada(self):
        r = decidir(*ejemplo("llamada_3_tercero_y_alucinacion"))
        self.assertIn("datos_de_tercero", r["avisos"])
        self.assertNotIn("comunicacion_externa", r["avisos"])   # La cita no existe en la llamada.
        self.assertNotIn("promesa", r["avisos"])                # Precio fijo: permitido.

    def test_negacion_no_es_tercero(self):
        r = decidir("[00:05] Ponerlo a nombre de otra persona no te da ningún beneficio.", {"alertas": {}})
        self.assertNotIn("datos_de_tercero", r["avisos"])


if __name__ == "__main__":
    unittest.main()
