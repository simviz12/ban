"""API FastAPI para el servicio de parseo y extracción bancaria.

Endpoints:
    GET  /health   → Estado del servicio
    POST /parse    → Parsea texto plano de correo bancario (regex determinista)
    POST /extract  → Extrae datos de imagen de comprobante (Gemini Vision)

Decisiones de diseño:
- /parse recibe text/plain para no forzar al cliente a serializar JSON cuando
  el input natural ya es texto.
- /extract recibe multipart/form-data (UploadFile) que es el estándar para
  archivos en REST.
- Ambos endpoints devuelven ParseResult (JSON) validado con Pydantic.
"""

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse

from app.models import ParseResult
from app.parsers import parse_email
from app.gemini_client import extract_from_image

app = FastAPI(
    title="Servicio de Parseo Bancario",
    description=(
        "Convierte correos de notificación bancaria y comprobantes de "
        "transferencia en estructuras de datos validadas y confiables."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg"}


@app.get("/health", summary="Health check del servicio")
async def health() -> str:
    """Verifica que el servicio está en línea."""
    return "OK"


@app.post(
    "/parse",
    response_model=ParseResult,
    summary="Parsear correo de notificación bancaria",
    description=(
        "Recibe el texto plano de un correo bancario y devuelve los campos "
        "estructurados. Los campos que no puedan extraerse con certeza se "
        "devuelven como null."
    ),
    openapi_extra={
        "requestBody": {
            "content": {
                "text/plain": {
                    "schema": {
                        "type": "string",
                        "description": "Texto plano del correo bancario"
                    }
                }
            },
            "required": True
        }
    }
)
async def parse_endpoint(request: Request) -> ParseResult:
    """Parsea un correo de notificación bancaria en texto plano.

    Acepta Content-Type: text/plain con el cuerpo del correo.
    """
    content_type = request.headers.get("content-type", "")
    if "text/plain" not in content_type:
        raise HTTPException(
            status_code=415,
            detail="Se requiere Content-Type: text/plain",
        )

    body_bytes = await request.body()
    if not body_bytes:
        raise HTTPException(
            status_code=422,
            detail="El cuerpo del request no puede estar vacío",
        )

    texto = body_bytes.decode("utf-8", errors="replace")
    resultado = parse_email(texto)
    return resultado


@app.post(
    "/extract",
    response_model=ParseResult,
    summary="Extraer datos de comprobante de pago (imagen JPG/PNG)",
    description=(
        "Recibe una imagen JPG o PNG de un comprobante bancario y usa "
        "Gemini Vision para extraer los campos estructurados. "
        "Requiere GEMINI_API_KEY configurada en el entorno."
    ),
)
async def extract_endpoint(
    file: UploadFile = File(..., description="Imagen JPG o PNG del comprobante"),
) -> ParseResult:
    """Extrae datos de un comprobante de pago usando Gemini Vision API."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de archivo no soportado: {content_type}. Use JPG o PNG.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=422,
            detail="El archivo de imagen está vacío",
        )

    resultado = await extract_from_image(image_bytes, content_type)
    return resultado
