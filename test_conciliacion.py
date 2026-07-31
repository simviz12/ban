"""Tests unitarios para la lógica de conciliación corregida."""

from datetime import datetime, timedelta
from decimal import Decimal
import pytest

from conciliacion_con_errores import Venta, CorreoBancario, conciliar, Resultado


def test_conciliacion_idempotencia_doble_consumo():
    """Prueba que un correo bancario no pueda ser conciliado más de una vez."""
    base = datetime(2026, 7, 14, 14, 30)

    # Dos ventas idénticas en monto y cercanas en tiempo
    ventas = [
        Venta(id="V-001", monto=Decimal("45.50"), momento=base),
        Venta(id="V-002", monto=Decimal("45.50"), momento=base + timedelta(minutes=5)),
    ]

    # Solo un correo bancario para ese monto
    correos = [
        CorreoBancario(id="C-001", banco="Banco Andino", monto=Decimal("45.50"), momento=base),
    ]

    resultados = conciliar(ventas, correos)

    # La primera venta debe conciliar exitosamente
    assert resultados[0].venta_id == "V-001"
    assert resultados[0].correo_id == "C-001"
    assert resultados[0].conciliada is True
    assert resultados[0].motivo == "coincidencia_confirmada"

    # La segunda venta debe fallar porque el correo ya fue consumido
    assert resultados[1].venta_id == "V-002"
    assert resultados[1].correo_id is None
    assert resultados[1].conciliada is False
    assert resultados[1].motivo == "sin_notificacion_coincidente"


def test_conciliacion_precision_decimal():
    """Prueba que sumas de Decimales coincidan de forma exacta, evitando errores de punto flotante."""
    base = datetime(2026, 7, 14, 14, 30)

    # 11.10 + 52.20 = 63.30 exacto con Decimal
    ventas = [
        Venta(id="V-001", monto=Decimal("11.10") + Decimal("52.20"), momento=base),
    ]

    correos = [
        CorreoBancario(id="C-001", banco="Banco Andino", monto=Decimal("63.30"), momento=base),
    ]

    resultados = conciliar(ventas, correos)

    assert resultados[0].conciliada is True
    assert resultados[0].correo_id == "C-001"


def test_conciliacion_fuera_de_ventana():
    """Prueba que rechace correos que están fuera de la ventana de tolerancia (90 mins)."""
    base = datetime(2026, 7, 14, 14, 30)

    ventas = [
        Venta(id="V-001", monto=Decimal("50.00"), momento=base),
    ]

    # Correo de notificación que llega 91 minutos después
    correos = [
        CorreoBancario(id="C-001", banco="Banco Andino", monto=Decimal("50.00"), momento=base + timedelta(minutes=91)),
    ]

    resultados = conciliar(ventas, correos)

    assert resultados[0].conciliada is False
    assert resultados[0].correo_id is None


def test_conciliacion_referencias_incompatibles():
    """Prueba que si ambos traen referencia, estas deben coincidir para conciliar."""
    base = datetime(2026, 7, 14, 14, 30)

    ventas = [
        Venta(id="V-001", monto=Decimal("50.00"), momento=base, referencia="REF-111"),
    ]

    correos = [
        CorreoBancario(id="C-001", banco="Banco Andino", monto=Decimal("50.00"), momento=base, referencia="REF-222"),
    ]

    resultados = conciliar(ventas, correos)

    assert resultados[0].conciliada is False
    assert resultados[0].correo_id is None
