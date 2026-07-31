# ANALISIS.md — Prueba Técnica Backend Python

---

## Parte 2 — Depuración: errores en `conciliacion_con_errores.py`

La función `conciliar()` se ejecutaba sin lanzar excepciones pero producía resultados
incorrectos. Se identificaron dos errores críticos.

---

### Error 1 — El correo bancario no se marcaba como consumido

#### Qué estaba mal

Dentro de `conciliar()`, cuando se encontraba un candidato válido, el código
confirmaba la conciliación pero **nunca actualizaba el estado del correo**:

```python
# Código original — con el error
if candidato is None:
    resultados.append(Resultado(venta.id, None, False, "sin_notificacion_coincidente"))
else:
    # FALTABA esta línea:
    # candidato.consumido = True
    resultados.append(Resultado(venta.id, candidato.id, True, "coincidencia_confirmada"))
```

#### Corrección aplicada

```python
# Código corregido
if candidato is None:
    resultados.append(Resultado(venta.id, None, False, "sin_notificacion_coincidente"))
else:
    candidato.consumido = True   # <-- esta es la corrección
    resultados.append(Resultado(venta.id, candidato.id, True, "coincidencia_confirmada"))
```

#### Por qué el código parecía correcto

El bucle interno incluía `if correo.consumido: continue`, lo que daba la impresión
de que el mecanismo de protección estaba activo. El error no estaba en el filtro sino
en que nadie activaba ese filtro después de una conciliación exitosa.

#### Consecuencia concreta en el negocio

Si dos ventas tenían el mismo monto en una ventana de tiempo cercana (por ejemplo,
dos clientes distintos pagan 45.50 con minutos de diferencia), ambas ventas se
aprobaban contra el **mismo único correo bancario**. El comerciante entregaba
producto o servicio dos veces creyendo que había recibido dos pagos, cuando en
realidad solo había recibido uno. Pérdida económica directa e inmediata.

---

### Error 2 — Comparación de montos con punto flotante

#### Qué estaba mal

Si los montos se construían sumando valores `float`, la comparación exacta fallaba:

```python
# En Python con float:
11.10 + 52.20  # -> 63.300000000000004  (no es 63.30)

# La comparación correo.monto != venta.monto fallaba aunque el monto fuera correcto
```

#### Corrección aplicada

El modelo `Venta` y `CorreoBancario` ya declaran el campo como `Decimal`.
La corrección es consistente: construir los valores usando `Decimal` desde el origen.

```python
# Incorrecto
venta = Venta(id="V-001", monto=11.10 + 52.20, ...)

# Correcto
venta = Venta(id="V-001", monto=Decimal("11.10") + Decimal("52.20"), ...)
# Decimal("11.10") + Decimal("52.20") == Decimal("63.30")  ->  True
```

#### Por qué el código parecía correcto

Matemáticamente `11.10 + 52.20 = 63.30` es cierto. El problema es que Python
usa IEEE 754 (punto flotante binario), donde la fracción decimal no siempre tiene
representación exacta. El error solo aparece en comparaciones de igualdad, no
en la pantalla donde el número se redondea visualmente.

#### Consecuencia concreta en el negocio

Ventas perfectamente legítimas donde el monto resultaba de la suma de dos o más
productos nunca cruzaban con el correo bancario equivalente. El sistema reportaba
"Pago no recibido" para un pago que sí había llegado. Generaba reclamos del
comerciante, intervención manual del equipo de soporte, y desconfianza en la
plataforma.

---

## Parte 3 — Decisión de diseño

### Situación

> El comerciante envía el pantallazo de una transferencia a las 14:32. Al buscar
> el correo del banco, encuentras uno que coincide exactamente en monto y en número
> de referencia, pero llegó a las 14:28 — es decir, cuatro minutos antes de que el
> comerciante enviara el pantallazo. ¿Lo consideras conciliado o lo rechazas?

### Decisión: el pago debe considerarse conciliado

### Justificación

El flujo físico real de un pago por WhatsApp es el siguiente:

1. El cliente abre su app bancaria y realiza la transferencia (14:28).
2. El banco procesa la transacción y dispara el correo electrónico al comercio
   de forma casi inmediata (14:28).
3. El cliente ve la confirmación en su pantalla, toma el pantallazo, abre WhatsApp,
   busca el chat del comercio y envía la imagen. Este proceso toma entre uno y
   varios minutos según la destreza del usuario (14:32).

Los cuatro minutos de diferencia son tiempo humano, no una anomalía. La secuencia
es completamente normal: el correo llega antes porque el banco procesa la
notificación en milisegundos, mientras que el ser humano tarda varios pasos para
enviar el pantallazo.

Además, monto y referencia coinciden exactamente. La referencia es un identificador
único generado por el banco para esa transacción específica. Que coincidan monto
y referencia es una evidencia muy fuerte de que son el mismo pago.

### Implicaciones de equivocarse en cada dirección

**Si se rechaza (falso negativo):**
- Un pago real queda bloqueado automáticamente.
- El comerciante no entrega el producto o servicio aunque el dinero ya está en su cuenta.
- El cliente reclama de inmediato.
- El equipo de soporte debe intervenir manualmente para desbloquear la venta.
- Se destruye la propuesta de valor del producto, que es exactamente eliminar ese
  trabajo manual.
- La experiencia del comerciante y del cliente empeora en cada transacción legítima
  que caiga en este patrón (que es el patrón más común).

**Si se acepta (falso positivo):**
- Existe el riesgo teórico de que alguien reutilice un pantallazo antiguo para
  cobrar dos veces por la misma transferencia.
- Este riesgo ya está mitigado en el sistema: `candidato.consumido = True` asegura
  que cada correo bancario solo puede conciliar una venta. Una vez que el correo
  de las 14:28 queda marcado como consumido, no puede usarse para aprobar ninguna
  otra venta, aunque alguien envíe el mismo pantallazo una segunda vez.

### Conclusión

Rechazar este pago generaría un falso negativo con impacto operacional directo
en cada transacción del día. Aceptarlo con la protección de idempotencia ya
implementada es la decisión correcta para el negocio.
