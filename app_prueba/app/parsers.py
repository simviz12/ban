"""Parsers deterministas para correos de notificación bancaria.

REGLA: Este módulo usa ÚNICAMENTE expresiones regulares (`re`) y lógica
determinista. No se usa IA/LLM aquí. El parseo es predecible, trazable
y testeable sin conexión a internet ni claves externas.

Bancos soportados:
- Banco Andino   → firma: @bancoandino.ec
- Banco Litoral  → firma: @bancodellitoral.ec
- Produbank      → firma: @produbank.ec

Extensibilidad: para agregar un cuarto banco basta con:
1. Añadir su `_parse_nuevo_banco()` con sus regex.
2. Registrarlo en `BANK_REGISTRY` con su firma de dominio.
"""

import re
from datetime import date, time
from decimal import Decimal, InvalidOperation

from app.models import ParseResult

# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------


def _to_decimal(raw: str | None) -> Decimal | None:
    """Convierte string de monto a Decimal. Soporta formato ecuatoriano.

    Formato ecuatoriano: '1.234,56' → separador de miles '.' y decimal ','
    Formato estándar:   '1234.56'  → separador decimal '.'
    Devuelve None si la cadena es None, vacía o no parseable.
    """
    if not raw:
        return None
    # Detectar formato ecuatoriano (coma como decimal): "1.234,56"
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    else:
        # Formato estándar: eliminar separador de miles si existe
        raw = raw.replace(",", "")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _to_date(raw: str | None) -> date | None:
    """Convierte string DD/MM/YYYY a date. Devuelve None si falla."""
    if not raw:
        return None
    try:
        day, month, year = raw.split("/")
        return date(int(year), int(month), int(day))
    except (ValueError, AttributeError):
        return None


def _to_time(raw: str | None) -> time | None:
    """Convierte string HH:MM o HH:MM:SS a time. Devuelve None si falla."""
    if not raw:
        return None
    try:
        parts = raw.split(":")
        if len(parts) == 2:
            return time(int(parts[0]), int(parts[1]))
        elif len(parts) == 3:
            return time(int(parts[0]), int(parts[1]), int(parts[2]))
        return None
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Parser: Banco Andino
# ---------------------------------------------------------------------------
# Formato de referencia (de correos_muestra.txt):
#   Tipo de movimiento : Credito
#   Concepto           : Transferencia recibida
#   Valor              : USD 45.50
#   Fecha              : 14/07/2026
#   Hora               : 14:28
#   Referencia         : 0294817365
#   Estado             : Aprobada

_ANDINO_TIPO = re.compile(
    r"Tipo\s+de\s+movimiento\s*:\s*(.+)", re.IGNORECASE
)
_ANDINO_CONCEPTO = re.compile(
    r"Concepto\s*:\s*(.+)", re.IGNORECASE
)
_ANDINO_VALOR = re.compile(
    r"Valor\s*:\s*USD\s+([\d.,]+)", re.IGNORECASE
)
_ANDINO_FECHA = re.compile(
    r"Fecha\s*:\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE
)
_ANDINO_HORA = re.compile(
    r"Hora\s*:\s*(\d{2}:\d{2}(?::\d{2})?)", re.IGNORECASE
)
_ANDINO_REFERENCIA = re.compile(
    r"Referencia\s*:\s*(\S+)", re.IGNORECASE
)
_ANDINO_ESTADO = re.compile(
    r"Estado\s*:\s*(.+)", re.IGNORECASE
)


def _parse_andino(texto: str) -> ParseResult:
    """Extrae campos del correo de Banco Andino mediante regex."""

    def _get(pattern: re.Pattern) -> str | None:
        m = pattern.search(texto)
        return m.group(1).strip() if m else None

    return ParseResult(
        banco="Banco Andino",
        tipo_movimiento=_get(_ANDINO_TIPO),
        concepto=_get(_ANDINO_CONCEPTO),
        monto=_to_decimal(_get(_ANDINO_VALOR)),
        fecha=_to_date(_get(_ANDINO_FECHA)),
        hora=_to_time(_get(_ANDINO_HORA)),
        estado=_get(_ANDINO_ESTADO),
        referencia=_get(_ANDINO_REFERENCIA),
    )


# ---------------------------------------------------------------------------
# Parser: Banco del Litoral
# ---------------------------------------------------------------------------
# Formato de referencia (de correos_muestra.txt):
#   ...el dia 14/07/2026 a las 16:05 su cuenta...
#   ...recibio una acreditacion por USD 128.75...
#   ...bajo el numero de referencia 883014925...
# NOTA: Este banco no informa tipo_movimiento ni estado de forma explícita.
# El concepto se infiere de la descripción narrativa del correo.

_LITORAL_FECHA = re.compile(
    r"el\s+dia\s+(\d{2}/\d{2}/\d{4})\s+a\s+las\s+(\d{2}:\d{2})",
    re.IGNORECASE,
)
_LITORAL_MONTO = re.compile(
    r"por\s+USD\s+([\d.,]+)", re.IGNORECASE
)
_LITORAL_REFERENCIA = re.compile(
    r"numero\s+de\s+referencia\s+(\d+)", re.IGNORECASE
)
_LITORAL_CONCEPTO = re.compile(
    r"correspondiente\s+a\s+(.+?)[\.\n]", re.IGNORECASE
)


def _parse_litoral(texto: str) -> ParseResult:
    """Extrae campos del correo de Banco del Litoral mediante regex."""
    fecha_hora_match = _LITORAL_FECHA.search(texto)
    fecha_raw = fecha_hora_match.group(1) if fecha_hora_match else None
    hora_raw = fecha_hora_match.group(2) if fecha_hora_match else None

    monto_m = _LITORAL_MONTO.search(texto)
    ref_m = _LITORAL_REFERENCIA.search(texto)
    concepto_m = _LITORAL_CONCEPTO.search(texto)

    return ParseResult(
        banco="Banco del Litoral",
        tipo_movimiento="Credito",  # El litoral solo notifica acreditaciones
        concepto=concepto_m.group(1).strip() if concepto_m else None,
        monto=_to_decimal(monto_m.group(1) if monto_m else None),
        fecha=_to_date(fecha_raw),
        hora=_to_time(hora_raw),
        estado=None,  # Banco del Litoral no reporta estado explícito
        referencia=ref_m.group(1) if ref_m else None,
    )


# ---------------------------------------------------------------------------
# Parser: Produbank
# ---------------------------------------------------------------------------
# Formato de referencia (de correos_muestra.txt):
#   - Operacion: Acreditacion por transferencia
#   - Monto: USD 1.234,56            ← formato ecuatoriano
#   - Fecha de proceso: 15/07/2026
#   - Hora de proceso: 09:40
#   - Nro. de referencia: 4471209833
#   - Canal: Banca en linea
#   - Estado: Procesada

_PRODUBANK_OPERACION = re.compile(
    r"-\s*Operacion\s*:\s*(.+)", re.IGNORECASE
)
_PRODUBANK_MONTO = re.compile(
    r"-\s*Monto\s*:\s*USD\s+([\d.,]+)", re.IGNORECASE
)
_PRODUBANK_FECHA = re.compile(
    r"-\s*Fecha\s+de\s+proceso\s*:\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE
)
_PRODUBANK_HORA = re.compile(
    r"-\s*Hora\s+de\s+proceso\s*:\s*(\d{2}:\d{2}(?::\d{2})?)", re.IGNORECASE
)
_PRODUBANK_REFERENCIA = re.compile(
    r"-\s*Nro\.\s+de\s+referencia\s*:\s*(\S+)", re.IGNORECASE
)
_PRODUBANK_ESTADO = re.compile(
    r"-\s*Estado\s*:\s*(.+)", re.IGNORECASE
)


def _parse_produbank(texto: str) -> ParseResult:
    """Extrae campos del correo de Produbank mediante regex."""

    def _get(pattern: re.Pattern) -> str | None:
        m = pattern.search(texto)
        return m.group(1).strip() if m else None

    return ParseResult(
        banco="Produbank",
        tipo_movimiento=_get(_PRODUBANK_OPERACION),
        concepto=_get(_PRODUBANK_OPERACION),  # En Produbank, operacion == concepto
        monto=_to_decimal(_get(_PRODUBANK_MONTO)),
        fecha=_to_date(_get(_PRODUBANK_FECHA)),
        hora=_to_time(_get(_PRODUBANK_HORA)),
        estado=_get(_PRODUBANK_ESTADO),
        referencia=_get(_PRODUBANK_REFERENCIA),
    )


# ---------------------------------------------------------------------------
# Registro de bancos y función unificadora
# ---------------------------------------------------------------------------

# Mapa de firma de dominio → función parser correspondiente
# Para agregar un nuevo banco: añadir entrada aquí y su función _parse_xxx()
BANK_REGISTRY: dict[str, tuple[str, object]] = {
    "@bancoandino.ec": ("Banco Andino", _parse_andino),
    "@bancodellitoral.ec": ("Banco del Litoral", _parse_litoral),
    "@produbank.ec": ("Produbank", _parse_produbank),
}


def parse_email(texto: str) -> ParseResult:
    """Identifica el banco por firma de dominio y parsea el correo.

    El banco se detecta buscando la firma '@dominio.ec' en el texto.
    Si no se reconoce el dominio, todos los campos se devuelven como None
    (regla de dato ausente).

    Args:
        texto: Texto completo del correo de notificación bancaria.

    Returns:
        ParseResult con los campos extraídos. Campos no extraíbles = None.
    """
    texto_lower = texto.lower()

    for firma, (_, parser_fn) in BANK_REGISTRY.items():
        if firma in texto_lower:
            return parser_fn(texto)

    # Banco no reconocido: todos los campos None
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
