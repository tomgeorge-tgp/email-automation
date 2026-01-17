
import polars as pl

def read_excel(file_path: str) -> pl.DataFrame:
    df = pl.read_excel(file_path)
    return df
