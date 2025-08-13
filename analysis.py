import polars as pl
from polars import col as c
import polars.selectors as cs
from tables import load_base_table

def margin_greater_than(value) -> pl.Expr:
    """
    Returns a Polars expression that filters rows where the 'margin_over_nadac' column is greater than the specified value.
    """
    return c.margin_over_nadac >= value

def margin_less_than(value) -> pl.Expr:
    """
    Returns a Polars expression that filters rows where the 'margin_over_nadac' column is less than the specified value.
    """
    return c.margin_over_nadac < value

def classify_margin(high, low) -> pl.Expr:
    """
    Classifies the 'margin_over_nadac' column into categories.
    """
    return (
        pl.when(margin_greater_than(high)).then(pl.lit("high"))
        .when(margin_less_than(low)).then(pl.lit("low"))
        .otherwise(pl.lit("other"))
        .alias("margin_classification")
    )

(
load_base_table()
.collect(engine='streaming')
.group_by(c.affiliate)
.agg(
    c.margin_over_nadac.median().alias("median_margin"),
    c.margin_over_nadac.mean().alias("mean_margin"),
)

.glimpse()
)