# Microservicio de Parseo y Conciliación Bancaria

Servicio backend en FastAPI diseñado para automatizar la extracción de datos de notificaciones bancarias de correo electrónico (vía regex deterministas) y la extracción de datos de comprobantes de transferencia en formato de imagen JPG/PNG (vía Vision API usando Gemini o Groq). Incluye también el motor corregido de conciliación bancaria.

---

## 🛠️ Desarrollo Local e Instalación Manual

Sigue estos pasos para levantar el servidor directamente usando **uvicorn**:

### 1. Clonar/acceder al directorio del microservicio
Asegúrate de estar posicionado en la carpeta `app_prueba`:
```bash
cd app_prueba
```

### 2. Configurar Variables de Entorno
Crea un archivo `.env` dentro de la carpeta `app_prueba/`:
```env
# Define al menos una de las dos para la extracción visual de imágenes:
GEMINI_API_KEY=tu_api_key_de_gemini
GROQ_API_KEY=tu_api_key_de_groq
```

### 3. Crear y activar Entorno Virtual
```bash
python -m venv venv
# En Windows (Powershell):
.\venv\Scripts\Activate.ps1
# En Linux/macOS:
source venv/bin/activate
```

### 4. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 5. Ejecutar el Servidor
Levanta el servidor con recarga automática:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
El servicio estará listo en `http://127.0.0.1:8000`.

---

## 🧪 Pruebas y Validación

### 1. Documentación Interactiva (Swagger)
Ingresa en tu navegador a:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
Desde allí puedes presionar "Try it out" en los endpoints `/parse` (para texto) o `/extract` (para imágenes) y realizar envíos en caliente.

### 2. Suite de Pruebas Automatizadas (Pytest)
Para ejecutar todos los tests unitarios mockeados:
```bash
pytest
```

### 3. Test de Imagen Real (Llamada a la API real)
Para validar que la comunicación externa con el proveedor de Vision (Gemini o Groq) funcione correctamente y extraiga datos de una imagen real:
```bash
python test_imagen_real.py
```

---

## 📂 Estructura del Repositorio

- `app/main.py`: Endpoints FastAPI (`/parse`, `/extract`, `/health`).
- `app/models.py`: Modelo Pydantic inmutable (`ParseResult`).
- `app/parsers.py`: Motores regex de parseo determinista para los bancos.
- `app/gemini_client.py`: Integración con la API de Vision de Gemini (`gemini-2.0-flash`) y Groq (`qwen/qwen3.6-27b`).
- `conciliacion_con_errores.py`: Módulo de conciliación bancaria.
- `test_imagen_real.py`: Script de integración para probar con imágenes reales de comprobantes.
- `docs/ANALISIS.md`: Explicación detallada de errores y respuestas de diseño.
- `docs/BITACORA_IA.md`: Registro de uso de asistentes de IA.

