from fastapi import FastAPI, HTTPException
from scraper import ScreenerScraper, StockNotFound, TableParsingError
from models import StockData

app = FastAPI(title="Screener.in Stock API", version="1.0.0")
scraper = ScreenerScraper()

@app.get("/api/stock/{symbol}", response_model=StockData)
async def get_stock(symbol: str):
    """
    Fetches stock data from Screener.in for the given symbol.
    - Tries consolidated data first.
    - Falls back to standalone data.
    """
    try:
        # Screener symbols are usually uppercase
        data = await scraper.scrape_stock(symbol.upper())
        return data
    except StockNotFound:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")
    except Exception as e:
        # Log the error in production
        print(f"Error fetching {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Welcome to Stock Analysis API. Use /api/stock/{symbol}"}
