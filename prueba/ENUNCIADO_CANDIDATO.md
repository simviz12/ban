# Prueba técnica — Desarrollador/a Backend Python

**Duración sugerida:** 2 h 15 min de trabajo efectivo
**Plazo de entrega:** 48 horas desde la recepción de este documento
**Stack:** Python 3.12, FastAPI, Pydantic

---

## 1. Contexto

Trabajamos en un producto que ayuda a micro-comercios a saber, sin llevar
contabilidad manual, cuánto dinero les entró realmente en el día.

El comerciante nos envía por WhatsApp la foto del comprobante de una
transferencia. Nosotros necesitamos confirmar que ese dinero efectivamente
llegó, y para eso lo cruzamos contra el correo de notificación que el banco
envía a la bandeja de entrada del propio comercio.

Esta prueba replica el componente más repetitivo y más crítico de ese flujo:
convertir correos de notificación bancaria, que cada banco escribe a su manera,
en una estructura de datos común y confiable.

Trabajarás con un conjunto de correos reales anonimizados de tres bancos
ecuatorianos (`correos_muestra.txt`).

---

## 2. Sobre el uso de asistentes de IA

**Puedes usar IA, y nos parece bien que lo hagas.** Copilot, Claude, ChatGPT,
Cursor, lo que uses en tu día a día. Aquí trabajamos así y no tiene sentido
evaluarte en condiciones distintas a las reales.

Lo que sí te pedimos es una cosa: **una bitácora de uso**, en un archivo
`BITACORA_IA.md`. No tiene que ser larga ni formal. Queremos ver:

- Qué le preguntaste y en qué momento del problema.
- Qué sugerencias aceptaste.
- **Qué sugerencias rechazaste y por qué.** Esta es la parte que más nos
  interesa. Nos dice más sobre tu criterio que cualquier otra cosa del
  ejercicio.

Si no usaste IA en alguna parte, escríbelo también y cuenta por qué no.

**Sesión en vivo:** después de la entrega haremos una sesión de 30 minutos por
videollamada con pantalla compartida. Ahí vas a explicar tu propio código y te
vamos a pedir que lo modifiques en vivo (agregar un banco, cambiar una regla).
Nada de trivia ni algoritmos de pizarrón: solo tu entrega. Ten a la mano el
entorno funcionando.

---

## 3. Parte 1 — Implementación (90 minutos sugeridos)

Construye un servicio en **FastAPI** con un endpoint `POST /parse`.

**Entrada:** el texto plano de un correo de notificación bancaria.

**Salida:** un JSON validado con Pydantic que contenga, como mínimo:

| Campo | Descripción |
|---|---|
| `banco` | Banco emisor de la notificación |
| `tipo_movimiento` | Naturaleza del movimiento reportado |
| `monto` | Valor de la operación |
| `fecha` | Fecha de la operación |
| `hora` | Hora de la operación |
| `referencia` | Número de referencia de la operación |

**Regla no negociable:** todo campo que no puedas extraer con certeza debe
devolverse como `null`. Nunca inventado, nunca con un valor por defecto, nunca
con una cadena vacía. Un dato equivocado en este sistema es peor que un dato
ausente: el dato ausente lo revisa un humano, el dato equivocado se contabiliza
como si fuera cierto.

**Pruebas:** incluye al menos dos pruebas automatizadas con `pytest`. Elige tú
qué vale la pena probar; esa elección también es parte de la evaluación.

Usa `correos_muestra.txt` como insumo.

---

## 4. Parte 2 — Depuración (30 minutos sugeridos)

En `conciliacion_con_errores.py` encontrarás una función de conciliación ya
escrita. Se ejecuta sin lanzar excepciones, pero **produce resultados
incorrectos**.

Hay **al menos un error**. Tu tarea:

1. Encontrarlo (o encontrarlos).
2. Corregirlo, entregando el archivo corregido.
3. Explicar por escrito, en `ANALISIS.md`: qué estaba mal, por qué el código
   parecía correcto, y **qué consecuencia concreta tendría ese error en el
   negocio** si llegara a producción.

El punto 3 pesa tanto como el 2.

---

## 5. Parte 3 — Decisión de diseño (15 minutos sugeridos)

Respuesta escrita, en `ANALISIS.md`. No hay código en esta parte.

> Un comerciante envía el pantallazo de una transferencia a las **14:32**. Al
> buscar el correo del banco, encuentras uno que coincide exactamente en monto
> y en número de referencia, pero llegó a las **14:28** — es decir, **cuatro
> minutos antes** de que el comerciante enviara el pantallazo.
>
> ¿Lo consideras conciliado o lo rechazas? Justifica tu decisión y explica qué
> implicaciones tendría equivocarse en cada dirección.

Queremos ver tu razonamiento, no una respuesta corta.

---

## 6. Formato de entrega

- **Repositorio Git** (GitHub, GitLab o un `.bundle`), con **historial de
  commits reales**. Un único commit final con todo el trabajo se considera
  entrega incompleta: parte de lo que evaluamos es cómo avanzas.
- **`README.md`** con instrucciones de ejecución: cómo instalar dependencias,
  cómo levantar el servicio, cómo correr las pruebas. Alguien que nunca vio tu
  proyecto debe poder ejecutarlo siguiendo solo eso.
- **`ANALISIS.md`** con las respuestas de las partes 2 y 3.
- **`BITACORA_IA.md`** con la bitácora descrita en la sección 2.

---

## 7. Cómo evaluamos

En orden de peso:

1. **Criterio sobre los datos.** Que no inventes lo que no está, que distingas
   lo que parece igual pero no lo es, que trates el dinero con el cuidado que
   requiere.
2. **Comprensión del negocio.** Que entiendas qué significa cada dato para el
   comerciante que está del otro lado.
3. **Calidad del código.** Legible, tipado, probado, fácil de extender a un
   cuarto banco.
4. **Honestidad técnica.** Si algo no te dio tiempo o no te salió, escríbelo en
   el README. Se valora más que disimularlo.

No evaluamos velocidad ni cantidad de líneas. Los tiempos sugeridos son una
referencia para que no te excedas, no una meta.

Cualquier duda sobre el enunciado, escríbenos antes de empezar. Preguntar bien
también cuenta a favor.
