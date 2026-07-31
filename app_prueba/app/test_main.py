"""Tests unitarios para los endpoints /parse y /health de la API.

Estrategia de pruebas:
- TestClient de httpx para llamadas HTTP en memoria (sin levantar servidor).
- Correos reales del archivo correos_muestra.txt como fixture.
- Se prueban los 3 bancos, casos de campo ausente y banco desconocido.
- No se mockea el parser: queremos detectar regresiones en los regex.

¿Qué vale la pena probar?
1. Que los campos críticos (monto, referencia) se extraigan correctamente.
2. Que el formato de monto ecuatoriano (1.234,56) funcione en Produbank.
3. Que campos ausentes devuelvan null, nunca string vacío.
4. Que un banco desconocido devuelva todos los campos null.
5. Que el modelo sea inmutable (frozen=True).
"""

import pytest
from decimal import Decimal
from datetime import date, time
from fastapi.testclient import TestClient

from app.main import app
from app.parsers import parse_email
from app.models import ParseResult

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures: correos de muestra
# ---------------------------------------------------------------------------

CORREO_ANDINO = """\
De: notificaciones@bancoandino.ec
Para: contacto@minimarketlaesquina.ec
Asunto: Notificacion de movimiento en su cuenta

Estimado cliente,

Le informamos que se ha registrado el siguiente movimiento en su cuenta
Corriente terminada en 4471:

  Tipo de movimiento : Credito
  Concepto           : Transferencia recibida
  Valor              : USD 45.50
  Fecha              : 14/07/2026
  Hora               : 14:28
  Referencia         : 0294817365
  Estado             : Aprobada

Banco Andino S.A.
Servicio de Notificaciones Electronicas
"""

CORREO_LITORAL = """\
De: alertas@bancodellitoral.ec
Para: contacto@minimarketlaesquina.ec
Asunto: Alerta de transaccion - Cuenta ***2210

Hola,

Le confirmamos que el dia 14/07/2026 a las 16:05 su cuenta de Ahorros
terminada en 2210 recibio una acreditacion por USD 128.75 correspondiente
a una transferencia interbancaria recibida. La operacion quedo registrada
bajo el numero de referencia 883014925 y el valor ya se encuentra
disponible en su saldo.

Banco del Litoral
Banca Electronica
"""

CORREO_PRODUBANK = """\
De: avisos@produbank.ec
Para: contacto@minimarketlaesquina.ec
Asunto: Produbank | Movimiento registrado en su cuenta

MOVIMIENTO REGISTRADO

- Cuenta: ****7788
- Operacion: Acreditacion por transferencia
- Monto: USD 1.234,56
- Fecha de proceso: 15/07/2026
- Hora de proceso: 09:40
- Nro. de referencia: 4471209833
- Canal: Banca en linea
- Estado: Procesada

Produbank
"""

CORREO_BANCO_DESCONOCIDO = """\
De: noreply@bancoxyz.com
Hola, su pago de 100.00 fue procesado.
"""

CORREO_ANDINO_DEBITO = """\
De: notificaciones@bancoandino.ec
Para: contacto@minimarketlaesquina.ec

Estimado cliente,

  Tipo de movimiento : Debito
  Concepto           : Pago de servicios
  Valor              : USD 62.00
  Fecha              : 15/07/2026
  Hora               : 11:12
  Referencia         : 0295044182
  Estado             : Aprobada

Banco Andino S.A.
"""


# ---------------------------------------------------------------------------
# Tests: endpoint GET /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == "OK"


# ---------------------------------------------------------------------------
# Tests: endpoint POST /parse — Banco Andino
# ---------------------------------------------------------------------------

class TestParseAndino:
    def test_banco_identificado_correctamente(self):
        response = client.post(
            "/parse",
            content=CORREO_ANDINO.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 200
        assert response.json()["banco"] == "Banco Andino"

    def test_monto_decimal_exacto(self):
        """El monto debe ser Decimal exacto, no float aproximado."""
        response = client.post(
            "/parse",
            content=CORREO_ANDINO.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 200
        # Pydantic serializa Decimal como string en JSON para preservar precisión
        data = response.json()
        assert data["monto"] == "45.50"

    def test_referencia_preservada_como_string(self):
        """La referencia debe ser string para preservar ceros iniciales."""
        response = client.post(
            "/parse",
            content=CORREO_ANDINO.encode(),
            headers={"Content-Type": "text/plain"},
        )
        data = response.json()
        assert data["referencia"] == "0294817365"

    def test_fecha_formato_iso(self):
        response = client.post(
            "/parse",
            content=CORREO_ANDINO.encode(),
            headers={"Content-Type": "text/plain"},
        )
        data = response.json()
        assert data["fecha"] == "2026-07-14"

    def test_hora_formato_iso(self):
        response = client.post(
            "/parse",
            content=CORREO_ANDINO.encode(),
            headers={"Content-Type": "text/plain"},
        )
        data = response.json()
        assert data["hora"] == "14:28:00"

    def test_tipo_movimiento_credito(self):
        response = client.post(
            "/parse",
            content=CORREO_ANDINO.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["tipo_movimiento"] == "Credito"

    def test_tipo_movimiento_debito(self):
        response = client.post(
            "/parse",
            content=CORREO_ANDINO_DEBITO.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["tipo_movimiento"] == "Debito"

    def test_estado_aprobada(self):
        response = client.post(
            "/parse",
            content=CORREO_ANDINO.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["estado"] == "Aprobada"


# ---------------------------------------------------------------------------
# Tests: endpoint POST /parse — Banco del Litoral
# ---------------------------------------------------------------------------

class TestParseLitoral:
    def test_banco_identificado(self):
        response = client.post(
            "/parse",
            content=CORREO_LITORAL.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["banco"] == "Banco del Litoral"

    def test_monto_litoral(self):
        response = client.post(
            "/parse",
            content=CORREO_LITORAL.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["monto"] == "128.75"

    def test_referencia_litoral(self):
        response = client.post(
            "/parse",
            content=CORREO_LITORAL.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["referencia"] == "883014925"

    def test_fecha_litoral(self):
        response = client.post(
            "/parse",
            content=CORREO_LITORAL.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["fecha"] == "2026-07-14"

    def test_estado_null_litoral(self):
        """Litoral no reporta estado, debe ser null."""
        response = client.post(
            "/parse",
            content=CORREO_LITORAL.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["estado"] is None


# ---------------------------------------------------------------------------
# Tests: endpoint POST /parse — Produbank
# ---------------------------------------------------------------------------

class TestParseProdubank:
    def test_banco_identificado(self):
        response = client.post(
            "/parse",
            content=CORREO_PRODUBANK.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["banco"] == "Produbank"

    def test_monto_formato_ecuatoriano(self):
        """1.234,56 en formato ecuatoriano debe parsearse como 1234.56."""
        response = client.post(
            "/parse",
            content=CORREO_PRODUBANK.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["monto"] == "1234.56"

    def test_referencia_produbank(self):
        response = client.post(
            "/parse",
            content=CORREO_PRODUBANK.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["referencia"] == "4471209833"

    def test_estado_procesada(self):
        response = client.post(
            "/parse",
            content=CORREO_PRODUBANK.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["estado"] == "Procesada"

    def test_fecha_produbank(self):
        response = client.post(
            "/parse",
            content=CORREO_PRODUBANK.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert response.json()["fecha"] == "2026-07-15"


# ---------------------------------------------------------------------------
# Tests: banco desconocido y casos edge
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_banco_desconocido_devuelve_todos_null(self):
        """Un banco no registrado debe devolver todos los campos null."""
        response = client.post(
            "/parse",
            content=CORREO_BANCO_DESCONOCIDO.encode(),
            headers={"Content-Type": "text/plain"},
        )
        data = response.json()
        assert data["banco"] is None
        assert data["monto"] is None
        assert data["referencia"] is None
        assert data["fecha"] is None

    def test_content_type_incorrecto_devuelve_415(self):
        response = client.post(
            "/parse",
            content=b"texto",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 415

    def test_body_vacio_devuelve_422(self):
        response = client.post(
            "/parse",
            content=b"",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 422

    def test_modelo_es_inmutable(self):
        """ParseResult con frozen=True no debe permitir modificación."""
        resultado = parse_email(CORREO_ANDINO)
        with pytest.raises(Exception):
            resultado.banco = "Otro banco"

    def test_monto_es_decimal_no_float(self):
        """El monto debe ser Decimal, no float, para evitar errores de precisión."""
        resultado = parse_email(CORREO_ANDINO)
        assert isinstance(resultado.monto, Decimal)

    def test_nunca_string_vacio_en_campos(self):
        """Los campos ausentes deben ser None, nunca string vacío."""
        resultado = parse_email(CORREO_BANCO_DESCONOCIDO)
        for field_name in ParseResult.model_fields:
            value = getattr(resultado, field_name)
            assert value != "", f"Campo '{field_name}' es string vacío, debe ser None"
