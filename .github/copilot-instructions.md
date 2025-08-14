# Copilot Instructions for Georgia NADAC Claims Data Processing

## Project Overview
- This project processes Georgia pharmacy claims by joining state claims, Medispan product info, and NADAC pricing for regulatory reporting and analysis.
- Data is modeled using Patito models in `models.py` (StateFile, NadacTable, Medispan, BaseTable).
- Data flows: Parquet files (state, NADAC, Medispan) → LazyFrame transforms (Polars) → joined and processed → output as BaseTable Parquet.

## Key Files & Structure
- `config.py`: All file paths and environment variable configuration.
- `models.py`: Patito data models for all tables.
- `tables.py`: Main ETL logic—functions to load, join, and process tables. `create_base_table` is the canonical ETL pipeline.
- `expressions.py`: Reusable Polars expressions for filtering, margin calculations, and classification.
- `analysis.py`: Example analysis/aggregation using the BaseTable (quantiles, stats, etc.).
- `requirements.txt`: Python dependencies (Polars, Patito, dotenv, duckdb).

## Data Flow & Patterns
- All data is loaded as Polars LazyFrames, transformed, and joined using explicit column lists from Patito models.
- Joins are performed with `.join` and `.join_asof` (see `tables.py`).
- All filtering and calculations use expressions from `expressions.py` for consistency.
- Output is written as Parquet using `.write_parquet`.

## Developer Workflows
- **Setup:**
  - Set environment variables for data locations (see `config.py`).
  - Install dependencies: `pip install -r requirements.txt`
- **ETL:**
  - Run or import `create_base_table` from `tables.py` to generate the main output.
- **Analysis:**
  - Use `analysis.py` as a template for custom queries/aggregations.
- **Testing:**
  - No formal test suite; validate by running ETL and inspecting output Parquet files.

## Conventions & Tips
- Always use Patito model `.columns` for selecting columns to ensure schema consistency.
- Use expressions from `expressions.py` for all margin and classification logic.
- All joins are on `ndc` and date columns; ensure date types are correct (cast as needed).
- Data files are expected in Parquet format; see `config.py` for expected locations.
- Avoid hardcoding paths—use environment variables and `config.py`.

## Integration Points
- External data: Parquet files for state claims, NADAC, and Medispan.
- No external APIs or services; all processing is local and file-based.

## Example: Creating the Base Table
```python
from tables import create_base_table
create_base_table(min_year=2024, tolerance='104w')
```

## Example: Analyzing Margins
```python
from analysis import get_margin_stats
stats = get_margin_stats()
print(stats)
```

---

For more, see `tables.py`, `analysis.py`, and the data dictionaries in `readme.md`.
