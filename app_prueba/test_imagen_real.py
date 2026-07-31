"""Script para probar la extracción real de la imagen usando Gemini API.

Para ejecutar este script:
1. Asegúrate de tener la variable de entorno GEMINI_API_KEY configurada.
2. Ejecuta: python app_prueba/test_imagen_real.py
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from app.gemini_client import extract_from_image


async def run_real_test():
    image_path = Path(__file__).parent.parent / "img" / "ChatGPT Image 31 jul 2026, 12_52_07.png"
    
    if not image_path.exists():
        print(f"[ERROR] No se encontro la imagen en {image_path.absolute()}")
        return

    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    if not gemini_key and not groq_key:
        print("[WARNING] Ni GEMINI_API_KEY ni GROQ_API_KEY encontradas en las variables de entorno.")
        print("Configure al menos una variable en su entorno o archivo .env.")
        return

    print(f"[INFO] Leyendo imagen real: {image_path.name}...")
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    provider = "Groq (llama-3.2-11b)" if groq_key else "Gemini (gemini-2.0-flash)"
    print(f"[INFO] Enviando imagen a la API de Vision usando {provider}...")
    try:
        resultado = await extract_from_image(image_bytes, "image/png")
        print("\n--- RESULTADO DE EXTRACCION (ParseResult) ---")
        print(f"Banco:             {resultado.banco}")
        print(f"Tipo Movimiento:    {resultado.tipo_movimiento}")
        print(f"Concepto:           {resultado.concepto}")
        print(f"Monto:              {resultado.monto} (Tipo: {type(resultado.monto).__name__})")
        print(f"Fecha:             {resultado.fecha}")
        print(f"Hora:              {resultado.hora}")
        print(f"Estado:            {resultado.estado}")
        print(f"Referencia:        {resultado.referencia}")
        print("-----------------------------------------------")
    except Exception as e:
        print(f"[ERROR] Error durante la extraccion: {e}")


if __name__ == "__main__":
    # Configurar el PYTHONPATH para que encuentre el paquete app
    import sys
    sys.path.append(str(Path(__file__).parent))
    
    asyncio.run(run_real_test())
