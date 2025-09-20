#!/usr/bin/env python3
"""
Script de prueba para verificar la integración del análisis en la app web
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


def test_analysis_integration():
    """Prueba la integración del análisis para la app web"""

    # Crear archivo de seeds de prueba
    test_keywords = ["marketing digital", "seo", "google ads"]

    with tempfile.TemporaryDirectory() as temp_dir:
        seeds_file = os.path.join(temp_dir, "test_seeds.txt")
        with open(seeds_file, 'w', encoding='utf-8') as f:
            for keyword in test_keywords:
                f.write(f"{keyword}\n")

        print(f"📝 Archivo de seeds creado: {seeds_file}")

        # Ejecutar análisis
        cmd = [
            sys.executable, "main.py",
            "--seeds-file", seeds_file,
            "--geo", "PE",
            "--language", "es",
            "--export", "csv",
            "--limit", "50"
        ]

        print(f"🚀 Ejecutando comando: {' '.join(cmd)}")

        result = subprocess.run(cmd, cwd=str(Path(__file__).parent), capture_output=True, text=True)

        print(f"📊 Código de salida: {result.returncode}")

        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False

        # Verificar archivos generados
        csv_files = [f for f in os.listdir("exports") if f.endswith('.csv')]
        print(f"📁 Archivos CSV encontrados: {csv_files}")

        if not csv_files:
            print("❌ No se encontraron archivos CSV")
            return False

        # Cargar y mostrar datos
        latest_csv = f"exports/{csv_files[-1]}"
        df = pd.read_csv(latest_csv)
        print(f"✅ Datos cargados: {len(df)} filas, {len(df.columns)} columnas")
        print(f"📋 Columnas: {list(df.columns)}")
        print(f"🎯 Primeras 5 filas:\n{df.head()}")

        return True

if __name__ == "__main__":
    print("🧪 Probando integración del análisis...")
    success = test_analysis_integration()
    if success:
        print("✅ ¡Integración exitosa!")
    else:
        print("❌ Error en la integración")