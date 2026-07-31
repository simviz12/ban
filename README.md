# Microservicio de Parseo y Conciliación Bancaria

Servicio backend en FastAPI diseñado para automatizar la extracción de datos de notificaciones bancarias de correo electrónico (vía regex deterministas) y la extracción de datos de comprobantes de transferencia en formato de imagen JPG/PNG (vía Gemini Vision OCR). Incluye también el motor corregido de conciliación bancaria.

---

## 🚀 Guía de Inicio Rápido (Docker-First)

Este proyecto está diseñado para levantarse inmediatamente con Docker sin necesidad de instalar dependencias locales.

### 1. Prerrequisitos
- Docker y Docker Compose instalados.
- Cuenta de Google AI Studio y una `GEMINI_API_KEY` (necesaria únicamente para el endpoint `/extract`).

### 2. Configurar Variables de Entorno
Cree un archivo `.env` en la carpeta `app_prueba` (o páselo en caliente a Docker):
```env
GEMINI_API_KEY=tu_api_key_aqui
```

### 3. Levantar el Servicio en Docker
Construya y levante el contenedor desde la carpeta `app_prueba/`:
```bash
cd app_prueba
docker build -t microservicio-bancos .
docker run -d -p 8000:8000 --env-file .env --name api-bancos microservicio-bancos
```
El servicio estará disponible en `http://localhost:8000`. Puede visitar la documentación interactiva de Swagger en `http://localhost:8000/docs`.

---

## 🛠️ Desarrollo Local e Instalación Manual

Si prefiere ejecutarlo fuera de Docker:

### 1. Crear y activar Entorno Virtual
```bash
python -m venv venv
# En Windows (Powershell):
.\venv\Scripts\Activate.ps1
# En Linux/macOS:
source venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r app_prueba/requirements.txt
```

### 3. Ejecutar el Servidor
```bash
cd app_prueba
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🧪 Suite de Pruebas Automatizadas

El proyecto cuenta con una cobertura completa de tests unitarios que simulan de forma controlada la interacción con la API de Gemini (mediante mocks) y validan rigurosamente las expresiones regulares y la conciliación.

Ejecutar todas las pruebas con reporte de cobertura:
```bash
pytest --cov=app_prueba/app --cov-report=term-missing
```

---

## 📂 Estructura del Repositorio

- `app_prueba/app/main.py`: Endpoints FastAPI (`/parse`, `/extract`, `/health`).
- `app_prueba/app/models.py`: Modelo Pydantic inmutable (`ParseResult`).
- `app_prueba/app/parsers.py`: Motores regex de parseo determinista para los bancos.
- `app_prueba/app/gemini_client.py`: Integración con el SDK `google-genai` para imágenes.
- `app_prueba/conciliacion_con_errores.py`: Módulo de conciliación corregido.
- `app_prueba/docs/ANALISIS.md`: Explicación detallada de errores y respuestas de diseño.
- `app_prueba/docs/BITACORA_IA.md`: Registro de uso de asistentes de IA.
