from models import StateFile, NadacTable, Medispan, BaseTable
import polars as pl
from polars import col as c
import polars.selectors as cs
from config import BASE_TABLE, STATE_DATA_DIR, NADAC_FILES, MEDISPAN_FILE
from expressions import ga_predicate, nadac_total, margin_over_nadac
from pathlib import Path

def load_state_table() -> pl.LazyFrame: 
    """
    Loads state data from parquet files, selects columns defined in StateFile, and sorts by 'ndc' and 'dos'.
    Returns a Polars LazyFrame.
    """
    return (
        pl.scan_parquet(STATE_DATA_DIR / "*.parquet")
        .select(StateFile.columns)
        .sort(by=['ndc','dos'])
    )

def load_nadac_table() -> pl.LazyFrame:
    """
    Loads NADAC data from parquet files, filters for matching effective and as_of dates,
    selects columns defined in NadacTable, and sorts by 'ndc' and 'effective_date'.
    Returns a Polars LazyFrame.
    """
    return (
        pl.scan_parquet(NADAC_FILES)
        .filter(c.effective_date == c.as_of)
        .with_columns([
            c.unit_price.cast(pl.Float64).round(4),  # Ensure unit_price is Float64
            c.effective_date.cast(pl.Date),
        ])
        .select(NadacTable.columns)
        .drop('as_of')
        .sort(by=['ndc','effective_date'])
    )

def load_medispan_table() -> pl.LazyFrame:
    """
    Loads Medispan data from a parquet file and selects columns defined in Medispan.
    Returns a Polars LazyFrame.
    """
    return (
        pl.scan_parquet(MEDISPAN_FILE)
        .select(Medispan.columns)
    )

def create_base_table(min_year: int = 2024, tolerance: str = '104w', output: Path = BASE_TABLE):
    """
    Loads and joins state data with Medispan and NADAC data for Georgia claims.
    Performs an asof join with NADAC data using a 104-week tolerance and calculates NADAC totals.
    Write output to a parquet file.
    """
    (
        # load data
        load_state_table()
        # filter for ga reportings
        .filter(ga_predicate())
        # filter for minimum year
        .filter(c.dos.dt.year() >= min_year)
        # add drug name
        .join(load_medispan_table(), on='ndc')
        # sort by ndc and dos for asof join
        .sort(['ndc', 'dos'])
        # load nadac and join to the closest nadac effective data less than or equal to dos. Only indclude those observations within the tolerance
        .join_asof(load_nadac_table(), left_on='dos', right_on='effective_date', by='ndc', strategy='backward', tolerance=tolerance)
        # filter out rows where nadac did not have a join
        .filter(c.unit_price.is_not_null())
        # calculate margin over nadac
        .with_columns(nadac_total(), margin_over_nadac())
        .collect(engine='streaming')
        .write_parquet(output)
    )

def load_base_table() -> pl.LazyFrame:
    """
    Loads the base table from a parquet file.
    Returns a Polars LazyFrame.
    """
    return pl.scan_parquet(BASE_TABLE).select(BaseTable.columns)
