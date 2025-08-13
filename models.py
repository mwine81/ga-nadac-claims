from patito import Model
from datetime import date

class StateFile(Model):
    ndc: str
    dos: date
    qty: float
    total: float
    affiliate: bool
    source: str

class NadacTable(Model):
    ndc: str
    unit_price: float
    effective_date: date
    as_of: date

class Medispan(Model):
    ndc: str
    product: str

class BaseTable(Model):
    ndc: str
    product: str
    dos: date
    qty: float
    total: float
    nadac_total: float
    margin_over_nadac: float
    affiliate: bool
    source: str
    effective_date: date

    
    
