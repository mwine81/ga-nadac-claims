import polars as pl
from polars import col as c
import polars.selectors as cs
from tables import load_base_table
from expressions import get_margin_quantile, margin_stats, cum_margin, median_quantity, unit_margin
import seaborn as sns
import numpy as np
from config import FIGURE_DIR

def get_all_margin_quantiles(lf: pl.LazyFrame = load_base_table(), min_quantile: int = 1, max_quantile: int = 99) -> pl.LazyFrame:
    """
    Retrieves all margin quantiles from min_quantile to max_quantile.

    """
    # list comprehension to generate the quantile expressions for values between min_quantile and max_quantile
    return pl.concat([lf.select(get_margin_quantile(q), pl.lit(q).alias('quantile') ) for q in pl.arange(min_quantile, max_quantile + 1, 1, eager=True)]).with_columns(cum_margin())

def get_margin_stats() -> dict:
    return (
    load_base_table()
    .select(margin_stats())
    .collect(engine='streaming')
    .to_dict(as_series=False)  # Convert to dictionary with series as values
    )

def starndard_margin_analysis(product: str = 'Buprenorphine HCl-Naloxone HCl Sublingual Tablet Sublingual 8-2 MG') -> pl.LazyFrame:
    base = (load_base_table()
        .filter(c.product == product)
    )
    median_qty = base.select(median_quantity()).collect(engine='streaming').item()
    return (
        base
        .group_by(c.dos)
    .agg(
        (unit_margin().median() * median_qty).round(2).alias('median_standardized_margin'),
        (unit_margin().mean() * median_qty).round(2).alias('mean_standardized_margin'),
        pl.len().alias('rx_count')
    )
    .sort(c.dos)
    )
