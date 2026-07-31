# --- Stage 1: Build dependencies ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Instalar herramientas de compilación básicas por si se requieren ruedas específicas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Compilar dependencias en un directorio local de ruedas para un arranque rápido en producción
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: Final minimal image ---
FROM python:3.12-slim AS runner

WORKDIR /app

# Copiar dependencias instaladas en el stage anterior
COPY --from=builder /root/.local /root/.local
COPY app/ /app/app/

# Asegurar que el path de los paquetes locales esté en el PYTHONPATH de Python
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
