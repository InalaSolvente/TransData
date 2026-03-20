from pathlib import Path
import pandas as pd

PROCESSED_DIR = Path("data/processed")

files = sorted(PROCESSED_DIR.glob("licitaciones_processed_*.csv"),
               key=lambda p: p.stat().st_mtime,
               reverse=True)

if not files:
    raise FileNotFoundError("No hay CSV procesados en data/processed")

latest = files[0]
df = pd.read_csv(latest)

print("Archivo:", latest)
print("Filas:", len(df))
print("Columnas:", list(df.columns))

if "comprador_nombre" in df.columns:
    print("\nNulls comprador_nombre:", df["comprador_nombre"].isna().sum())
    print("Ejemplos comprador_nombre (10):")
    print(df["comprador_nombre"].dropna().head(10))
else:
    print("\n❌ No existe columna comprador_nombre")

print("\nHead:")
print(df.head())