"""Conciliacion de ventas reportadas por el comercio contra las notificaciones
bancarias recibidas en su bandeja de correo.

CORRECCIONES APLICADAS vs la version original con errores:

BUG 1 — Doble consumo (idempotencia rota):
    PROBLEMA: Al encontrar un candidato valido, el codigo confirmaba la
    conciliacion pero NUNCA marcaba el correo como consumido.
    `candidato.consumido = True` faltaba por completo.
    IMPACTO: El mismo correo bancario podia conciliarse con multiples ventas.
    Un deposito de $45.50 podia aprobarse dos veces -> perdida economica directa.
    FIX: Agregar `candidato.consumido = True` antes de registrar el resultado.

BUG 2 — Precision decimal con float:
    PROBLEMA: `11.10 + 52.20` con float en Python = 63.300000000000004.
    La comparacion `correo.monto != venta.monto` nunca coincide aunque
    matematicamente sea el mismo valor.
    IMPACTO: Ventas con monto calculado (suma de items) nunca se concilian.
    El sistema reporta "sin pago" para pagos que si llegaron.
    FIX: Usar `Decimal` para todos los montos monetarios desde el origen.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

VENTANA_TOLERANCIA = timedelta(minutes=90)


@dataclass
class Venta:
    """Venta que el comerciante reporto enviando un comprobante."""

    id: str
    monto: Decimal          # FIX BUG 2: Decimal en lugar de float
    momento: datetime
    referencia: str | None = None


@dataclass
class CorreoBancario:
    """Notificacion bancaria ya parseada."""

    id: str
    banco: str
    monto: Decimal          # FIX BUG 2: Decimal en lugar de float
    momento: datetime
    referencia: str | None = None
    consumido: bool = False


@dataclass
class Resultado:
    venta_id: str
    correo_id: str | None
    conciliada: bool
    motivo: str


def _dentro_de_ventana(venta: Venta, correo: CorreoBancario) -> bool:
    """Indica si la notificacion cae dentro de la ventana temporal aceptada."""
    return abs(venta.momento - correo.momento) <= VENTANA_TOLERANCIA


def _referencias_compatibles(venta: Venta, correo: CorreoBancario) -> bool:
    """Si ambas partes traen referencia, deben coincidir. Si falta alguna, no bloquea."""
    if venta.referencia is None or correo.referencia is None:
        return True
    return venta.referencia == correo.referencia


def conciliar(ventas: list[Venta], correos: list[CorreoBancario]) -> list[Resultado]:
    """Empareja cada venta reportada con la notificacion bancaria que le corresponde.

    Devuelve un resultado por cada venta recibida, en el mismo orden de entrada.
    Garantia de idempotencia: cada correo solo puede conciliar una venta.
    """
    resultados: list[Resultado] = []

    for venta in ventas:
        candidato: CorreoBancario | None = None

        for correo in correos:
            if correo.consumido:
                continue
            if correo.monto != venta.monto:
                continue
            if not _dentro_de_ventana(venta, correo):
                continue
            if not _referencias_compatibles(venta, correo):
                continue
            candidato = correo
            break

        if candidato is None:
            resultados.append(
                Resultado(venta.id, None, False, "sin_notificacion_coincidente")
            )
        else:
            candidato.consumido = True  # FIX BUG 1: marcar consumido para garantizar idempotencia
            resultados.append(
                Resultado(venta.id, candidato.id, True, "coincidencia_confirmada")
            )

    return resultados


if __name__ == "__main__":
    base = datetime(2026, 7, 14, 14, 30)

    ventas = [
        # FIX BUG 2: Decimal("11.10") + Decimal("52.20") == Decimal("63.30") exacto
        Venta(id="V-001", monto=Decimal("11.10") + Decimal("52.20"), momento=base),
        Venta(id="V-002", monto=Decimal("45.50"), momento=base + timedelta(minutes=20)),
        Venta(id="V-003", monto=Decimal("45.50"), momento=base + timedelta(minutes=55)),
    ]
    correos = [
        CorreoBancario("C-001", "Banco Andino", Decimal("63.30"), base - timedelta(minutes=3), "0294817001"),
        CorreoBancario("C-002", "Banco Andino", Decimal("45.50"), base + timedelta(minutes=18), "0294817365"),
    ]

    for resultado in conciliar(ventas, correos):
        print(resultado)
