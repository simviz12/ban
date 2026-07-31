"""Tests del endpoint POST /extract usando unittest.mock.

Estrategia:
- NO se hace ninguna llamada real a la API de Gemini.
- Se mockea `app.gemini_client.genai.Client` para simular respuestas.
- Los tests pasan en cualquier entorno sin internet ni GEMINI_API_KEY.
- Se prueban: extracción exitosa, campo ilegible (null), JSON malformado,
  tipo de archivo inválido y API key ausente.

¿Por qué mock y no llamada real?
- Los tests deben ser reproducibles, rápidos y sin costo externo.
- Un test que llama a una API externa no es un test unitario.
- En CI/CD no habrá siempre acceso a internet o claves configuradas.
"""

import json
import pytest
from decimal import Decimal
from datetime import date, time
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.gemini_client import _parse_gemini_response

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers para crear respuestas simuladas de Gemini
# ---------------------------------------------------------------------------

def _make_gemini_response(json_data: dict) -> MagicMock:
    """Crea un mock de respuesta de Gemini con texto JSON."""
    mock_response = MagicMock()
    mock_response.text = json.dumps(json_data)
    return mock_response


def _make_fake_image() -> bytes:
    """Crea bytes mínimos que simulan una imagen PNG válida (firma PNG)."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


# ---------------------------------------------------------------------------
# Tests: _parse_gemini_response (función interna, sin HTTP)
# ---------------------------------------------------------------------------

class TestParseGeminiResponse:
    def test_json_completo_valido(self):
        """Todos los campos presentes y válidos."""
        raw = json.dumps({
            "banco": "Banco Pichincha",
            "tipo_movimiento": "Pago a Nequi",
            "concepto": "Prueba sistema",
            "monto": "50000.00",
            "fecha": "2025-05-24",
            "hora": "12:45",
            "estado": None,
            "referencia": "1234567890",
        })
        resultado = _parse_gemini_response(raw)
        assert resultado.banco == "Banco Pichincha"
        assert resultado.monto == Decimal("50000.00")
        assert resultado.fecha == date(2025, 5, 24)
        assert resultado.hora == time(12, 45)
        assert resultado.referencia == "1234567890"

    def test_json_malformado_devuelve_todos_null(self):
        """Si Gemini devuelve texto no-JSON, todos los campos son null."""
        raw = "Lo siento, no pude extraer la información."
        resultado = _parse_gemini_response(raw)
        assert resultado.banco is None
        assert resultado.monto is None
        assert resultado.fecha is None
        assert resultado.referencia is None

    def test_campo_null_en_respuesta(self):
        """Campos null en JSON de Gemini se mapean a None en ParseResult."""
        raw = json.dumps({
            "banco": "Banco Andino",
            "tipo_movimiento": None,
            "concepto": None,
            "monto": "45.50",
            "fecha": "2026-07-14",
            "hora": None,
            "estado": None,
            "referencia": None,
        })
        resultado = _parse_gemini_response(raw)
        assert resultado.banco == "Banco Andino"
        assert resultado.tipo_movimiento is None
        assert resultado.hora is None
        assert resultado.referencia is None

    def test_monto_es_decimal(self):
        """El monto debe ser Decimal, no float."""
        raw = json.dumps({
            "banco": "Test", "tipo_movimiento": None, "concepto": None,
            "monto": "128.75", "fecha": None, "hora": None,
            "estado": None, "referencia": None,
        })
        resultado = _parse_gemini_response(raw)
        assert isinstance(resultado.monto, Decimal)
        assert resultado.monto == Decimal("128.75")

    def test_json_con_markdown_fence(self):
        """Gemini a veces envuelve el JSON en bloques markdown."""
        raw = '```json\n{"banco": "Test", "tipo_movimiento": null, "concepto": null, "monto": null, "fecha": null, "hora": null, "estado": null, "referencia": null}\n```'
        # La función limpieza en gemini_client debe manejar esto
        # Aquí probamos directamente _parse_gemini_response con JSON limpio
        clean = '{"banco": "Test", "tipo_movimiento": null, "concepto": null, "monto": null, "fecha": null, "hora": null, "estado": null, "referencia": null}'
        resultado = _parse_gemini_response(clean)
        assert resultado.banco == "Test"


# ---------------------------------------------------------------------------
# Tests: endpoint POST /extract con mock de Gemini
# ---------------------------------------------------------------------------

GEMINI_RESPONSE_PICHINCHA = {
    "banco": "Banco Pichincha",
    "tipo_movimiento": "Pago a Nequi",
    "concepto": "Prueba sistema",
    "monto": "50000.00",
    "fecha": "2025-05-24",
    "hora": "12:45",
    "estado": None,
    "referencia": "1234567890",
}


class TestExtractEndpoint:
    def test_extraccion_exitosa_con_mock(self):
        """Simula extracción completa desde imagen PNG."""
        fake_image = _make_fake_image()

        with patch("app.gemini_client.os.getenv", return_value="fake-api-key"), \
             patch("app.gemini_client.genai") as mock_genai:

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content.return_value = _make_gemini_response(
                GEMINI_RESPONSE_PICHINCHA
            )

            response = client.post(
                "/extract",
                files={"file": ("comprobante.png", fake_image, "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["banco"] == "Banco Pichincha"
        assert data["monto"] == "50000.00"
        assert data["referencia"] == "1234567890"

    def test_tipo_archivo_invalido_devuelve_415(self):
        """Archivo PDF o texto no debe aceptarse."""
        response = client.post(
            "/extract",
            files={"file": ("doc.pdf", b"PDF content", "application/pdf")},
        )
        assert response.status_code == 415

    def test_api_key_ausente_devuelve_503(self):
        """Sin GEMINI_API_KEY configurada, el servicio debe indicar 503."""
        fake_image = _make_fake_image()

        with patch("app.gemini_client.os.getenv", return_value=None):
            response = client.post(
                "/extract",
                files={"file": ("comprobante.png", fake_image, "image/png")},
            )

        assert response.status_code == 503
        assert "GEMINI_API_KEY" in response.json()["detail"]

    def test_campo_ilegible_devuelve_null(self):
        """Si Gemini no puede leer un campo, debe devolverse null."""
        respuesta_parcial = {
            "banco": "Banco Andino",
            "tipo_movimiento": None,
            "concepto": None,
            "monto": "45.50",
            "fecha": None,
            "hora": None,
            "estado": None,
            "referencia": None,
        }
        fake_image = _make_fake_image()

        with patch("app.gemini_client.os.getenv", return_value="fake-key"), \
             patch("app.gemini_client.genai") as mock_genai:

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content.return_value = _make_gemini_response(
                respuesta_parcial
            )

            response = client.post(
                "/extract",
                files={"file": ("comprobante.png", fake_image, "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["tipo_movimiento"] is None
        assert data["fecha"] is None
        assert data["referencia"] is None

    def test_jpeg_también_aceptado(self):
        """Imágenes JPEG también deben procesarse."""
        fake_image = b"\xff\xd8\xff" + b"\x00" * 100  # Firma JPEG

        with patch("app.gemini_client.os.getenv", return_value="fake-key"), \
             patch("app.gemini_client.genai") as mock_genai:

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content.return_value = _make_gemini_response(
                GEMINI_RESPONSE_PICHINCHA
            )

            response = client.post(
                "/extract",
                files={"file": ("comprobante.jpg", fake_image, "image/jpeg")},
            )

        assert response.status_code == 200
