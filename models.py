from typing import List, Optional, Dict, Union, Any
from pydantic import BaseModel

class DocumentItem(BaseModel):
    title: str
    url: str

class Documents(BaseModel):
    annual_reports: List[DocumentItem] = []
    credit_ratings: List[DocumentItem] = []
    concalls: List[DocumentItem] = []
    announcements: List[DocumentItem] = []

class Header(BaseModel):
    market_cap: Optional[str] = None
    current_price: Optional[str] = None
    high_low: Optional[str] = None
    stock_pe: Optional[str] = None
    book_value: Optional[str] = None
    dividend_yield: Optional[str] = None
    roce: Optional[str] = None
    roe: Optional[str] = None
    face_value: Optional[str] = None

class StockData(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    header: Header
    about: Optional[str] = None
    pros: List[str] = []
    cons: List[str] = []

    # Tables are dynamic, so we use List[Dict] to accommodate varying columns (years/quarters)
    quarterly_results: List[Dict[str, Any]] = []
    profit_loss: List[Dict[str, Any]] = []
    balance_sheet: List[Dict[str, Any]] = []
    cash_flow: List[Dict[str, Any]] = []
    ratios: List[Dict[str, Any]] = []
    shareholding_pattern: List[Dict[str, Any]] = []
    peers: List[Dict[str, Any]] = []

    documents: Documents
