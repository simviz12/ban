"""Conciliacion de ventas reportadas por el comercio contra las notificaciones
bancarias recibidas en su bandeja de correo."""

from dataclasses import dataclass
from datetime import datetime, timedelta

VENTANA_TOLERANCIA = timedelta(minutes=90)


@dataclass
class Venta:
    """Venta que el comerciante reporto enviando un comprobante."""

    id: str
    monto: float
    momento: datetime
    referencia: str | None = None


@dataclass
class CorreoBancario:
    """Notificacion bancaria ya parseada."""

    id: str
    banco: str
    monto: float
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
            resultados.append(Resultado(venta.id, None, False, "sin_notificacion_coincidente"))
        else:
            resultados.append(Resultado(venta.id, candidato.id, True, "coincidencia_confirmada"))

    return resultados


if __name__ == "__main__":
    base = datetime(2026, 7, 14, 14, 30)

    ventas = [
        Venta(id="V-001", monto=11.10 + 52.20, momento=base),
        Venta(id="V-002", monto=45.50, momento=base + timedelta(minutes=20)),
        Venta(id="V-003", monto=45.50, momento=base + timedelta(minutes=55)),
    ]
    correos = [
        CorreoBancario("C-001", "Banco Andino", 63.30, base - timedelta(minutes=3), "0294817001"),
        CorreoBancario("C-002", "Banco Andino", 45.50, base + timedelta(minutes=18), "0294817365"),
    ]

    for resultado in conciliar(ventas, correos):
        print(resultado)
