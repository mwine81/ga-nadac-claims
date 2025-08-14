import polars as pl
from polars import col as c
import polars.selectors as cs
from tables import load_base_table
from expressions import get_margin_quantile, margin_stats, cum_margin
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

