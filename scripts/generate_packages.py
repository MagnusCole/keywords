import glob
import os
import sys

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from templates.report_template import create_premium_report


def find_latest_file(pattern):
    """Find the most recent file matching the pattern."""
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)


def generate_package(niche_name, output_dir):
    # Find latest data files
    keywords_file = find_latest_file("exports/keyword_analysis_*.csv")
    clusters_file = find_latest_file("exports/clusters_summary_*.csv")
    
    if not keywords_file or not clusters_file:
        print(f"Error: Could not find data files for {niche_name}")
        return
    
    # Load data from CSVs
    keywords_df = pd.read_csv(keywords_file)
    clusters_df = pd.read_csv(clusters_file)
    
    # Convert to dict format for template
    data = {
        "keywords": keywords_df.to_dict('records'),
        "clusters": clusters_df.to_dict('records')
    }
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate PDF
    pdf_path = os.path.join(output_dir, f"{niche_name.replace(' ', '_').lower()}_report.pdf")
    create_premium_report(data, pdf_path, niche_name)
    
    # Copy CSVs to output directory
    import shutil
    shutil.copy(keywords_file, os.path.join(output_dir, "keyword_analysis.csv"))
    shutil.copy(clusters_file, os.path.join(output_dir, "clusters_summary.csv"))
    
    print(f"Package generated for {niche_name}")


# Generate for each niche
generate_package(
    "Marketing Digital Perú", "reports/marketing_digital_peru"
)
generate_package("Clínicas Médicas", "reports/clinicas_medicas")
generate_package("Cursos Online", "reports/cursos_online")
