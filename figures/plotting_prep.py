
from analysis import get_all_margin_quantiles
import polars as pl

def prepare_quantile_distribution(min_quantile: int = 1, max_quantile: int = 99) -> pl.DataFrame:
    """Collect quantile thresholds with cumulative margin for plotting.

    Returns a DataFrame with columns:
      quantile, margin_over_nadac (threshold), cumulative_margin.
    """
    qlf = get_all_margin_quantiles(min_quantile=min_quantile, max_quantile=max_quantile)
    # The first column is the quantile threshold value, rename explicitly
    # Use collect_schema().names() to avoid resolving the full LazyFrame schema at runtime
    first_col = qlf.collect_schema().names()[0]
    return (
        qlf.rename({first_col: 'margin_threshold'})
           .collect(engine='streaming')
           .sort('quantile')
    )