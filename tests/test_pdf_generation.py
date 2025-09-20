#!/usr/bin/env python3
"""
Script para probar la generación completa de reportes desde la app
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from templates.report_template import create_premium_report


def test_pdf_generation():
    """Prueba la generación completa de PDFs"""

    # Simular datos como los que vendrían de la app
    test_keywords = ["marketing digital", "seo", "google ads"]

    with tempfile.TemporaryDirectory() as temp_dir:
        # Crear archivo de seeds
        seeds_file = os.path.join(temp_dir, "seeds.txt")
        with open(seeds_file, 'w', encoding='utf-8') as f:
            for keyword in test_keywords:
                f.write(f"{keyword}\n")

        # Ejecutar análisis
        cmd = [
            sys.executable, "main.py",
            "--seeds-file", seeds_file,
            "--geo", "PE",
            "--language", "es",
            "--export", "csv",
            "--limit", "20"
        ]

        print("🔍 Ejecutando análisis...")
        result = subprocess.run(cmd, cwd=str(Path(__file__).parent), capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Error en análisis: {result.stderr}")
            return False

        # Encontrar archivos CSV generados
        csv_files = [f for f in os.listdir("exports") if f.endswith('.csv') and 'keyword_analysis' in f]
        if not csv_files:
            print("❌ No se encontraron archivos de keywords")
            return False

        # Cargar datos
        latest_csv = f"exports/{csv_files[-1]}"
        keywords_df = pd.read_csv(latest_csv)

        # Buscar archivo de clusters
        cluster_files = [f for f in os.listdir("exports") if f.endswith('.csv') and 'clusters' in f]
        clusters_df = pd.read_csv(f"exports/{cluster_files[-1]}") if cluster_files else pd.DataFrame()

        # Preparar datos para el template
        data = {
            "keywords": keywords_df.head(50).to_dict('records'),
            "clusters": clusters_df.to_dict('records') if not clusters_df.empty else []
        }

        # Generar PDF
        pdf_path = os.path.join(temp_dir, "test_report.pdf")
        print(f"📄 Generando PDF: {pdf_path}")

        try:
            create_premium_report(data, pdf_path, "Marketing Digital Perú")
            print("✅ PDF generado exitosamente!")

            # Verificar que el archivo existe
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                print(f"📊 Tamaño del PDF: {file_size} bytes")
                return True
            else:
                print("❌ El archivo PDF no se creó")
                return False

        except Exception as e:
            print(f"❌ Error generando PDF: {e}")
            return False

if __name__ == "__main__":
    print("🧪 Probando generación completa de reportes...")
    success = test_pdf_generation()
    if success:
        print("🎉 ¡Generación de reportes funcionando perfectamente!")
    else:
        print("💥 Error en la generación de reportes")