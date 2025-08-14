import polars as pl
from polars import col as c
import polars.selectors as cs

def ga_predicate() -> pl.Expr:
    """
    Returns a Polars expression that matches rows where the 'source' column contains 'ga' (case-insensitive).
    """
    return c.source.str.contains("(?i)ga")

def nadac_total() -> pl.Expr:
    """
    Calculates the total NADAC cost based on quantity and unit price.
    Returns a Polars expression.
    """
    return (c.qty * c.unit_price).round(2).alias('nadac_total')

def margin_over_nadac() -> pl.Expr:
    return (c.total - nadac_total()).round(2).alias('margin_over_nadac')

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

def get_margin_quantile(quantile: int) -> pl.Expr:
    """
    Returns a Polars expression that retrieves the margin base on the quantile.
    """
    return c.margin_over_nadac.quantile(quantile/100)

def mean_margin_over_nadac() -> pl.Expr:
    return c.margin_over_nadac.mean().round(2).alias('mean_margin_over_nadac')

def median_margin_over_nadac() -> pl.Expr:
    return c.margin_over_nadac.median().round(2).alias('median_margin_over_nadac')

def std_margin_over_nadac() -> pl.Expr:
    return c.margin_over_nadac.std().round(2).alias('std_margin_over_nadac')

def min_margin_over_nadac() -> pl.Expr:
    return c.margin_over_nadac.min().round(2).alias('min_margin_over_nadac')

def max_margin_over_nadac() -> pl.Expr:
    return c.margin_over_nadac.max().round(2).alias('max_margin_over_nadac')

def margin_stats() -> list[pl.Expr]:
    return [
        mean_margin_over_nadac(),
        median_margin_over_nadac(),
        std_margin_over_nadac(),
        min_margin_over_nadac(),
        max_margin_over_nadac()
    ]

def cum_margin() -> pl.Expr:
    return c.margin_over_nadac.cum_sum().round(2).alias('cumulative_margin')