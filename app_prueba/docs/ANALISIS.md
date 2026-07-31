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

### Decisión: El pago debe considerarse conciliado.

### Justificación Técnica y de Negocio

El desfase de **4 minutos** es una anomalía temporal humana completamente normal y esperable dentro del flujo físico y operativo de un pago:

1. **Iniciación (14:28):** El cliente realiza la transferencia bancaria desde su banca móvil.
2. **Procesamiento Bancario (14:28):** El banco procesa e inmediatamente despacha la notificación automatizada de correo electrónico al comercio (ingresando al sistema en milisegundos).
3. **Interacción Humana (14:28 - 14:32):** El cliente ve la confirmación en pantalla, toma captura del comprobante, abre WhatsApp, busca el chat del comerciante y envía la imagen. Este proceso manual toma tiempo humano promedio (en este caso, 4 minutos).

Dado que **el monto y el número de referencia coinciden exactamente**, y sabiendo que el número de referencia es un identificador único global generado de forma unívoca por el banco emisor para ese movimiento específico, no existe posibilidad matemática de que pertenezcan a eventos independientes.

---

### Implicaciones de equivocarse en cada dirección

#### A. Si se rechaza el pago (Falso Negativo)
* **Error Operativo:** Rechazar una transacción legítima del cliente debido a una regla de tiempo estricta e incorrecta.
* **Impacto en Negocio:** El comerciante retendrá el producto o servicio aunque el dinero ya se encuentre acreditado en su cuenta bancaria. Esto genera de inmediato fricción en el cliente final, reclamos directos al soporte del comercio y la necesidad de intervención manual para destrabar el flujo.
* **Daño al Producto:** Se destruye la propuesta de valor del microservicio, que es automatizar la conciliación para eliminar la carga administrativa.

#### B. Si se acepta el pago (Riesgo de Falso Positivo)
* **Error Operativo:** Riesgo teórico de fraude mediante la reutilización de comprobantes antiguos.
* **Mitigación del Sistema:** Este riesgo de fraude queda **totalmente mitigado (reducido a cero)** gracias al control de **idempotencia** que implementa el motor (`correo.consumido = True`). En cuanto el primer cliente concilia su venta, el correo de las 14:28 se marca como consumido en la base de datos. Cualquier intento posterior de reenviar el mismo comprobante para otra venta será rechazado automáticamente al evaluar el estado del correo.

### Conclusión
Rechazar la transacción por un desfase de 4 minutos introduce una fricción operativa innecesaria e incorrecta en transacciones 100% legítimas. Aceptarlo bajo la arquitectura de protección y banderas de idempotencia ya implementadas es la decisión correcta para el negocio y el usuario.
