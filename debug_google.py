#!/usr/bin/env python3
"""Test para debuggear el HTML de Google Search"""

import asyncio
import httpx
import logging
from selectolax.parser import HTMLParser

logging.basicConfig(level=logging.INFO)

async def debug_google_html():
    """Analizar el HTML de Google Search para encontrar related searches"""
    
    async with httpx.AsyncClient() as client:
        try:
            url = "https://www.google.com/search?q=marketing&hl=es&gl=es"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
            }
            
            response = await client.get(url, headers=headers)
            html = response.text
            
            print(f"Status: {response.status_code}")
            print(f"HTML length: {len(html)}")
            
            # Guardar HTML para análisis
            with open("google_search.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("HTML guardado en google_search.html")
            
            # Buscar posibles selectores de related searches
            parser = HTMLParser(html)
            
            print("\n=== Buscando 'Búsquedas relacionadas' ===")
            # Buscar texto "búsquedas relacionadas" o "related searches"
            for element in parser.css('*'):
                text = element.text(strip=True).lower()
                if 'relacionad' in text or 'related' in text:
                    print(f"Found: {text}")
                    print(f"Element: {element.tag} {element.attributes}")
                    # Buscar elementos hermanos
                    parent = element.parent
                    if parent:
                        for sibling in parent.css('a'):
                            link_text = sibling.text(strip=True)
                            if link_text and len(link_text) > 2:
                                print(f"  Related link: {link_text}")
            
            print("\n=== Buscando posibles patrones ===")
            # Buscar varios patrones comunes
            selectors = [
                'div[data-st] a',
                'div[class*="related"] a',
                '[role="listitem"] a',
                'div[data-hveid] a',
                'div[data-ved] a',
                'a[ping]',
                'div[jsname] a',
                '[data-q]'
            ]
            
            for selector in selectors:
                elements = parser.css(selector)
                print(f"\nSelector '{selector}': {len(elements)} elementos")
                for i, elem in enumerate(elements[:5]):  # Solo primeros 5
                    text = elem.text(strip=True)
                    if text:
                        print(f"  {i}: {text}")
                        
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_google_html())