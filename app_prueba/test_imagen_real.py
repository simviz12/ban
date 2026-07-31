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


async def test_real():
    image_path = Path("img/ChatGPT Image 31 jul 2026, 12_52_07.png")
    
    if not image_path.exists():
        print(f"❌ No se encontró la imagen en {image_path.absolute()}")
        return

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ GEMINI_API_KEY no encontrada en las variables de entorno.")
        print("Para realizar una llamada real a la API de Gemini, configure la variable en su entorno o archivo .env.")
        return

    print(f"🔍 Leyendo imagen real: {image_path.name}...")
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    print("🤖 Enviando imagen a Gemini (gemini-2.0-flash) con el prompt de extracción...")
    try:
        resultado = await extract_from_image(image_bytes, "image/png")
        print("\n✨ --- RESULTADO DE EXTRACCIÓN (ParseResult) --- ✨")
        print(f"🏛️ Banco:             {resultado.banco}")
        print(f"🔄 Tipo Movimiento:    {resultado.tipo_movimiento}")
        print(f"📝 Concepto:           {resultado.concepto}")
        print(f"💰 Monto:              {resultado.monto} (Tipo: {type(resultado.monto).__name__})")
        print(f"📅 Fecha:             {resultado.fecha}")
        print(f"⏰ Hora:              {resultado.hora}")
        print(f"🚦 Estado:            {resultado.estado}")
        print(f"🆔 Referencia:        {resultado.referencia}")
        print("-----------------------------------------------")
    except Exception as e:
        print(f"❌ Error durante la extracción: {e}")


if __name__ == "__main__":
    # Configurar el PYTHONPATH para que encuentre el paquete app
    import sys
    sys.path.append(str(Path(__file__).parent))
    
    asyncio.run(test_real())
