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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "symbol": "HDFCBANK",
                    "company_name": "HDFC Bank Ltd",
                    "header": {
                        "market_cap": "₹ 14,00,000 Cr.",
                        "current_price": "₹ 1,700",
                        "high_low": "₹ 1,750 / 1,400",
                        "stock_pe": "18.5",
                        "book_value": "₹ 550",
                        "dividend_yield": "1.10 %",
                        "roce": "6.5 %",
                        "roe": "17.0 %",
                        "face_value": "₹ 1.00"
                    },
                    "about": "HDFC Bank Limited is an Indian banking and financial services company...",
                    "pros": ["Company has delivered good profit growth of 20% CAGR over last 5 years"],
                    "cons": ["Stock is trading at 3.5 times its book value"],
                    "quarterly_results": [
                        {"Sep 2023": "45000", "Dec 2023": "48000"}
                    ],
                    "profit_loss": [
                         {"Mar 2023": "170000", "Mar 2024": "200000"}
                    ],
                    "balance_sheet": [],
                    "cash_flow": [],
                    "ratios": [],
                    "shareholding_pattern": [],
                    "peers": [],
                    "documents": {
                        "annual_reports": [
                            {"title": "Financial Year 2024", "url": "https://example.com/ar2024.pdf"}
                        ],
                        "credit_ratings": [],
                        "concalls": [
                             {"title": "Jan 2024 - Transcript", "url": "https://example.com/concall.pdf"}
                        ],
                        "announcements": []
                    }
                }
            ]
        }
    }
