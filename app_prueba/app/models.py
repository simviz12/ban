"""Modelos Pydantic para la validación y serialización de datos bancarios.

Principio fundamental: todo campo que no pueda extraerse con certeza DEBE
ser None. Un dato ausente es preferible a un dato incorrecto en un sistema
financiero: el dato ausente lo revisa un humano, el dato equivocado se
contabiliza como verdadero.

Decisión de diseño:
- `frozen=True` garantiza inmutabilidad del resultado una vez parseado.
- `Decimal` en lugar de `float` para evitar errores de precisión numérica
  (ej: 11.10 + 52.20 con float ≠ 63.30 exacto).
"""

from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ParseResult(BaseModel):
    """Resultado estructurado del parseo de un correo o comprobante bancario.

    Todos los campos son opcionales y pueden ser None cuando no se puedan
    extraer con certeza absoluta desde el texto o imagen de entrada.
    """

    model_config = ConfigDict(frozen=True)

    banco: str | None
    """Nombre del banco emisor de la notificación (ej: 'Banco Andino')."""

    tipo_movimiento: str | None
    """Naturaleza del movimiento: 'Credito', 'Debito', 'Acreditacion', etc."""

    concepto: str | None
    """Descripción del concepto o motivo del movimiento."""

    monto: Decimal | None
    """Valor de la operación. Siempre Decimal; nunca float para evitar
    errores de precisión acumulados en comparaciones monetarias."""

    fecha: date | None
    """Fecha de la operación en formato ISO (YYYY-MM-DD)."""

    hora: time | None
    """Hora de la operación en formato ISO (HH:MM o HH:MM:SS)."""

    estado: str | None
    """Estado de la operación reportado por el banco (ej: 'Aprobada')."""

    referencia: str | None
    """Número de referencia único de la operación, como string para
    preservar ceros iniciales u otros formatos especiales."""
