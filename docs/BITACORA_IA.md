# BITACORA_IA.md — Bitácora de Desarrollo con IA

En esta bitácora se registran las interacciones, decisiones, sugerencias aceptadas y rechazadas durante el desarrollo del microservicio de parseo y conciliación bancaria.

---

## 1. Planificación General e Inicio del Proyecto

### Herramientas utilizadas
- Google Antigravity Coding Assistant (Claude 3.5 Sonnet / Gemini 3.5 Flash).

### Preguntas/Prompts del desarrollador
- Entendimiento del enunciado técnico y preparación de la estructura de carpetas en `app_prueba`.
- Definición del flujo GitFlow con commits atómicos de Conventional Commits.

---

## 2. Decisiones de Diseño y Sugerencias Aceptadas

1. **Uso de Decimal para Representación Financiera (Paso 2 y Paso 7)**:
   - *Sugerencia*: Usar `Decimal` en el modelo Pydantic y en la lógica de conciliación.
   - *Razón de aceptación*: El tipo `float` de Python tiene imprecisiones de representación IEEE 754 inherentes que impiden comparaciones de igualdad confiables en dinero.
2. **Determinismo vs IA en el Parseo de Correos (Paso 3)**:
   - *Sugerencia*: Usar expresiones regulares estructuradas e indexadas por el dominio de correo emisor para el endpoint `/parse`.
   - *Razón de aceptación*: Es el método más rápido, barato, 100% predecible, sin latencias de red y fácilmente extensible.
3. **Mocks Completos para el Testing de Gemini Vision (Paso 6)**:
   - *Sugerencia*: Simular por completo la API de `google-genai` usando `unittest.mock.patch`.
   - *Razón de aceptación*: Las pruebas deben correr localmente y en pipelines de CI/CD de forma rápida, determinista, libre de costo y sin requerir internet ni claves reales.

---

## 3. Sugerencias Rechazadas y Justificación Técnica

1. **Uso de LLM/Gemini para parsear correos de texto plano**:
   - *Sugerencia de la IA*: "Podríamos usar Gemini en ambos endpoints `/parse` y `/extract` unificando la lógica con un único agente de visión y texto".
   - *Decisión*: **Rechazada**.
   - *Razón*: El parseo de notificaciones de texto plano de bancos ya conocidos tiene un formato estructurado altamente predecible. Implementar un LLM ahí añade latencia innecesaria (segundos vs milisegundos), costos de API, y el riesgo no nulo de alucinación (ej. confundir un número de cuenta con la referencia). El procesamiento determinista con regex cumple con la regla no negociable de "nunca inventar datos".
2. **Generación de un esquema dinámico JSON Schema de Pydantic directamente en la llamada a Gemini**:
   - *Sugerencia de la IA*: "Usa `response_mime_type="application/json"` con `response_schema` en la configuración de la generación para que Gemini autovalide la salida".
   - *Decisión*: **Rechazada**.
   - *Razón*: Aunque el SDK de Gemini v1.0.0+ lo soporta, forzar esquemas estrictos a nivel de API puede causar excepciones o fallos duros de parseo si hay caracteres extraños en la imagen. Se prefirió recibir un JSON plano flexible en el prompt de temperatura 0.0 y realizar la conversión segura y manejo de nulos de forma controlada en nuestro código Python (`gemini_client.py`), garantizando robustez y que los campos inválidos sean devueltos como `null` en lugar de romper el endpoint.

---

## 4. Conclusiones

La combinación de desarrollo estructurado modular y la asistencia de IA permitió implementar un flujo robusto en menos tiempo, garantizando la inmutabilidad de los datos financieros, el determinismo del parseo y la idempotencia en la conciliación.
