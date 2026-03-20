from pathlib import Path
import pandas as pd

PROCESSED_DIR = Path("data/processed")


def load_latest_processed() -> pd.DataFrame:
    files = sorted(
        PROCESSED_DIR.glob("licitaciones_processed_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError("No se encontraron archivos procesados en data/processed")
    latest = files[0]
    print(f"Cargando archivo: {latest}")
    return pd.read_csv(latest)


def clean_buyer_name(s: pd.Series) -> pd.Series:
    s = s.astype("string")
    s = s.str.strip()
    s = s.replace({"": pd.NA})
    return s


def build_ranking(df: pd.DataFrame) -> pd.DataFrame:
    if "comprador_nombre" not in df.columns:
        raise KeyError("No existe la columna comprador_nombre en el CSV procesado.")

    df = df.copy()
    df["comprador_nombre"] = clean_buyer_name(df["comprador_nombre"])
    df = df.dropna(subset=["comprador_nombre"])

    ranking = (
        df.groupby("comprador_nombre")
        .size()
        .reset_index(name="cantidad_licitaciones")
        .sort_values("cantidad_licitaciones", ascending=False)
    )
    return ranking


def main():
    df = load_latest_processed()
    ranking = build_ranking(df)

    print("\nTop 10 compradores:\n")
    print(ranking.head(10))

    out_path = PROCESSED_DIR / "ranking_compradores.csv"
    ranking.to_csv(out_path, index=False, encoding="utf-8")
    print(f"\n[OK] Ranking guardado en: {out_path}")
    print(f"[INFO] Compradores únicos: {ranking.shape[0]}")


if __name__ == "__main__":
    main()