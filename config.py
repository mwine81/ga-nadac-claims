from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

STATE_DATA_DIR = Path(os.getenv("STATE_REPORTS")) #type: ignore
NADAC_FILES = Path(os.getenv("NADAC_DIR")) / 'NADAC*.parquet' #type: ignore
MEDISPAN_FILE = Path(os.getenv("MEDISPAN_FILE")) #type: ignore
BASE_TABLE = Path(os.getenv("BASE_TABLE")) #type: ignore
FIGURE_DIR = Path('figures/fig')
DATA_DIR = Path(os.getenv("DATA_DIR")) #type: ignore
GA_DATABASE = DATA_DIR / 'ga.db' #type: ignore
