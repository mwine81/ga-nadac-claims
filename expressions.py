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