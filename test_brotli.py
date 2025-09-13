#!/usr/bin/env python3
"""Test simple para debuggear Brotli"""

import asyncio
import httpx
import brotli
import logging

logging.basicConfig(level=logging.DEBUG)

async def test_brotli():
    """Test simple de descompresión Brotli"""
    
    async with httpx.AsyncClient() as client:
        try:
            url = "http://suggestqueries.google.com/complete/search?client=chrome&q=test&hl=es"
            response = await client.get(url)
            
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Content-Encoding: {response.headers.get('content-encoding')}")
            print(f"Content type: {type(response.content)}")
            print(f"Content length: {len(response.content)}")
            
            if response.headers.get('content-encoding') == 'br':
                print("Intentando descomprimir Brotli...")
                try:
                    decompressed = brotli.decompress(response.content)
                    print(f"Descomprimido exitosamente! Tamaño: {len(decompressed)}")
                    text = decompressed.decode('utf-8')
                    print(f"Texto: {text[:200]}...")
                except Exception as e:
                    print(f"Error en descompresión: {e}")
                    print(f"Tipo de error: {type(e)}")
                    
                    # Intentar con httpx
                    print("Intentando con response.text...")
                    try:
                        text = response.text
                        print(f"httpx text: {text[:200]}...")
                    except Exception as e2:
                        print(f"Error con response.text: {e2}")
            else:
                print("No hay compresión Brotli")
                print(f"Texto: {response.text[:200]}...")
                
        except Exception as e:
            print(f"Error general: {e}")

if __name__ == "__main__":
    asyncio.run(test_brotli())