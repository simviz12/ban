"""Cliente de la API de Google Gemini para extracción de datos desde imágenes.

Este módulo maneja ÚNICAMENTE el procesamiento de imágenes (comprobantes
de transferencia en JPG/PNG). El parseo de texto plano de correos se hace
con regex deterministas en parsers.py, no aquí.

Decisiones de diseño:
- Se usa `google-genai` SDK v1.0.0+ (cliente oficial).
- Modelo: gemini-2.0-flash (rápido, económico, con visión).
- El prompt obliga a Gemini a devolver JSON estricto con los 8 campos.
- Cualquier campo ilegible en la imagen se mapea a null (nunca inventado).
- La API key se lee de la variable de entorno GEMINI_API_KEY, nunca
  hardcodeada en el código.

Sobre el uso de IA para esta tarea:
- Usamos Gemini únicamente para OCR de imágenes porque el procesamiento
  visual no puede hacerse de forma determinista con regex.
- Para correos de texto (POST /parse) NO usamos Gemini: es costoso,
  lento y no determinista para texto estructurado.
"""

import base64
import json
import os
from decimal import Decimal, InvalidOperation
from datetime import date, time

from dotenv import load_dotenv

from app.models import ParseResult

load_dotenv()

# Prompt estructurado para forzar salida JSON estricta
_EXTRACTION_PROMPT = """
Analiza esta imagen de un comprobante de pago bancario y extrae los datos.

Devuelve ÚNICAMENTE un objeto JSON válido con exactamente estos 8 campos:
{
  "banco": "nombre del banco o null si no se puede leer",
  "tipo_movimiento": "tipo de operacion o null",
  "concepto": "descripcion del concepto o null",
  "monto": "numero decimal como string (ej: '45.50') o null",
  "fecha": "fecha en formato YYYY-MM-DD o null",
  "hora": "hora en formato HH:MM o null",
  "estado": "estado de la transaccion o null",
  "referencia": "numero de referencia como string o null"
}

REGLAS ESTRICTAS:
- Si un campo no aparece claramente en la imagen, devuelve null (sin comillas).
- El monto debe ser un número decimal como string, sin símbolo de moneda.
- Si el monto tiene formato latinoamericano (ej: '50.000,00'), conviértelo a '50000.00'.
- La fecha debe estar en ISO 8601: YYYY-MM-DD.
- La hora en formato 24h: HH:MM.
- NO inventes datos. NO uses valores por defecto.
- Devuelve SOLO el JSON, sin texto adicional, sin markdown, sin explicaciones.
"""


def _safe_decimal(value: str | None) -> Decimal | None:
    """Convierte string a Decimal de forma segura."""
    if not value:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def _safe_date(value: str | None) -> date | None:
    """Convierte string ISO a date de forma segura."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _safe_time(value: str | None) -> time | None:
    """Convierte string HH:MM a time de forma segura."""
    if not value:
        return None
    try:
        parts = str(value).split(":")
        if len(parts) >= 2:
            return time(int(parts[0]), int(parts[1]))
        return None
    except (ValueError, TypeError):
        return None


def _parse_gemini_response(raw_json: str) -> ParseResult:
    """Convierte la respuesta JSON de Gemini en un ParseResult validado.

    Si el JSON está malformado o faltan campos, se devuelve None para
    esos campos específicos.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        # Si Gemini devuelve algo que no es JSON puro, todos los campos son None
        return ParseResult(
            banco=None,
            tipo_movimiento=None,
            concepto=None,
            monto=None,
            fecha=None,
            hora=None,
            estado=None,
            referencia=None,
        )

    return ParseResult(
        banco=data.get("banco") or None,
        tipo_movimiento=data.get("tipo_movimiento") or None,
        concepto=data.get("concepto") or None,
        monto=_safe_decimal(data.get("monto")),
        fecha=_safe_date(data.get("fecha")),
        hora=_safe_time(data.get("hora")),
        estado=data.get("estado") or None,
        referencia=str(data["referencia"]) if data.get("referencia") else None,
    )


async def extract_from_image(image_bytes: bytes, content_type: str) -> ParseResult:
    """Envía una imagen a Gemini Vision y extrae los datos del comprobante.

    Args:
        image_bytes: Contenido binario de la imagen JPG/PNG.
        content_type: MIME type de la imagen ('image/jpeg' o 'image/png').

    Returns:
        ParseResult con los datos extraídos. Campos ilegibles = None.

    Raises:
        HTTPException 503: Si la API key no está configurada.
        HTTPException 502: Si Gemini devuelve un error inesperado.
    """
    from fastapi import HTTPException

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "GEMINI_API_KEY no configurada. "
                "Define la variable de entorno antes de usar /extract."
            ),
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # Convertir imagen a base64 para el SDK
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=content_type,
                                data=image_bytes,
                            )
                        ),
                        types.Part(text=_EXTRACTION_PROMPT),
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.0,   # Determinismo máximo
                max_output_tokens=512,
            ),
        )

        raw_text = response.text or ""
        # Limpiar posibles bloques markdown que Gemini a veces agrega
        raw_text = raw_text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1]
            raw_text = raw_text.rsplit("```", 1)[0]

        return _parse_gemini_response(raw_text.strip())

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error al comunicarse con la API de Gemini: {str(exc)}",
        ) from exc
