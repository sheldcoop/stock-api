import asyncio
import random
import logging
from typing import Optional, Dict, List, Any
from io import StringIO

import aiohttp
from bs4 import BeautifulSoup
import pandas as pd

from models import StockData, Header, Documents, DocumentItem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
]

class StockNotFound(Exception):
    pass

class TableParsingError(Exception):
    pass

class ScreenerScraper:
    BASE_URL = "https://www.screener.in"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def fetch_html(self, symbol: str) -> str:
        """
        Fetches HTML for the given symbol.
        Tries consolidated URL first, then fallback to standalone.
        """
        async with aiohttp.ClientSession() as session:
            # 1. Try Consolidated URL
            consolidated_url = f"{self.BASE_URL}/company/{symbol}/consolidated/"
            logger.info(f"Fetching {consolidated_url}")
            try:
                async with session.get(consolidated_url, headers=self._get_headers()) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 404:
                        logger.warning(f"Consolidated data not found for {symbol}. Falling back to standalone.")
                    else:
                        response.raise_for_status()
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching consolidated URL: {e}")

            # 2. Fallback to Standalone URL
            standalone_url = f"{self.BASE_URL}/company/{symbol}/"
            logger.info(f"Fetching {standalone_url}")
            async with session.get(standalone_url, headers=self._get_headers()) as response:
                if response.status == 404:
                    raise StockNotFound(f"Stock {symbol} not found")
                response.raise_for_status()
                return await response.text()

    async def fetch_peers(self, company_id: str) -> List[Dict[str, Any]]:
        """
        Fetches the peers table using the company ID.
        """
        if not company_id:
            return []

        url = f"{self.BASE_URL}/api/company/{company_id}/peers/"
        logger.info(f"Fetching peers from {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers()) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'lxml')
                        return self._extract_table(soup, None, table_only=True)
                    else:
                        logger.warning(f"Failed to fetch peers: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching peers: {e}")
            return []

    def _clean_df(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Cleans the DataFrame:
        - Replaces NaN with None
        - Converts to list of dictionaries
        """
        # Replace NaN with None.
        # Note: 'where' replaces values where condition is False.
        # So we want where(notnull) to keep values, else replace with None.
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient='records')

    def _extract_table(self, soup: BeautifulSoup, section_id: Optional[str], table_only: bool = False) -> List[Dict[str, Any]]:
        if table_only:
            # If soup is just the table HTML or container
            target = soup
        else:
            section = soup.find('section', id=section_id)
            if not section:
                return []
            target = section

        table = target.find('table')
        if not table:
            return []

        try:
            # Use StringIO to avoid FutureWarning
            df_list = pd.read_html(StringIO(str(table)))
            if df_list:
                return self._clean_df(df_list[0])
        except Exception as e:
            logger.error(f"Error parsing table {section_id if section_id else 'peers'}: {e}")

        return []

    def _parse_header(self, soup: BeautifulSoup) -> Header:
        header_data = {}
        top_ratios = soup.find('ul', id='top-ratios')
        if top_ratios:
            for li in top_ratios.find_all('li'):
                name_span = li.find('span', class_='name')
                value_span = li.find('span', class_='value')
                if name_span and value_span:
                    name = name_span.get_text(strip=True)
                    value = value_span.get_text(strip=True)

                    if "Market Cap" in name:
                        header_data['market_cap'] = value
                    elif "Current Price" in name:
                        header_data['current_price'] = value
                    elif "High / Low" in name:
                        header_data['high_low'] = value
                    elif "Stock P/E" in name:
                        header_data['stock_pe'] = value
                    elif "Book Value" in name:
                        header_data['book_value'] = value
                    elif "Dividend Yield" in name:
                        header_data['dividend_yield'] = value
                    elif "ROCE" in name:
                        header_data['roce'] = value
                    elif "ROE" in name:
                        header_data['roe'] = value
                    elif "Face Value" in name:
                        header_data['face_value'] = value

        return Header(**header_data)

    def _parse_documents(self, soup: BeautifulSoup) -> Documents:
        docs = Documents()

        # Locate the main document section by ID
        doc_section_container = soup.find('section', id='documents')

        if not doc_section_container:
            # Fallback: try finding headers "Annual Reports" etc directly if section id is missing
            return self._parse_documents_fallback(soup)

        # Inside the section, there are multiple columns with class 'documents'
        # e.g., <div class="documents flex-column"> <h3>Title</h3> ... </div>
        doc_columns = doc_section_container.find_all('div', class_='documents')
        if not doc_columns:
            # Try finding direct h3 headers inside the section if columns structure changed
            return self._parse_documents_fallback(doc_section_container)

        for col in doc_columns:
            h3 = col.find('h3')
            if not h3:
                continue

            section_title = h3.get_text(strip=True).lower()

            links = []

            # Helper to add links
            def add_link(title, href):
                if href and title.lower() != "all":
                    links.append(DocumentItem(title=title, url=href))

            if "concall" in section_title:
                # For Concalls, try to get the date from the parent <li> if possible
                for li in col.find_all('li'):
                    # Get text nodes direct child of li
                    date_text = "".join([t for t in li.contents if isinstance(t, str)]).strip()

                    for a in li.find_all('a'):
                        href = a.get('href')
                        a_text = a.get_text(strip=True)

                        if date_text:
                            final_title = f"{date_text} - {a_text}"
                        else:
                            final_title = a_text

                        add_link(final_title, href)
            else:
                # Standard parsing for other sections
                for a in col.find_all('a'):
                    href = a.get('href')
                    title = a.get_text(strip=True) or "Document"
                    add_link(title, href)

            if "annual report" in section_title:
                docs.annual_reports.extend(links)
            elif "credit rating" in section_title:
                docs.credit_ratings.extend(links)
            elif "concall" in section_title:
                docs.concalls.extend(links)
            elif "announcement" in section_title:
                docs.announcements.extend(links)

        return docs

    def _parse_documents_fallback(self, soup: BeautifulSoup) -> Documents:
        """
        Fallback method if the standard structure fails.
        Searches for specific headers and looks for links in their vicinity.
        """
        docs = Documents()

        def find_links_for_header(header_text_part):
            links = []
            # Find h3 containing the text
            header = soup.find(lambda tag: tag.name == 'h3' and header_text_part in tag.get_text(strip=True).lower())
            if not header:
                return links

            # Look for ul/links in the parent or siblings
            container = header.parent
            for a in container.find_all('a'):
                href = a.get('href')
                title = a.get_text(strip=True)
                if href and title.lower() != 'all':
                    links.append(DocumentItem(title=title, url=href))
            return links

        docs.annual_reports = find_links_for_header("annual report")
        docs.credit_ratings = find_links_for_header("credit rating")
        docs.concalls = find_links_for_header("concall")
        docs.announcements = find_links_for_header("announcement")

        return docs

    def _parse_pros_cons(self, soup: BeautifulSoup) -> (List[str], List[str]):
        pros = []
        cons = []

        pros_section = soup.find('div', class_='pros')
        if pros_section:
            pros = [li.get_text(strip=True) for li in pros_section.find_all('li')]

        cons_section = soup.find('div', class_='cons')
        if cons_section:
            cons = [li.get_text(strip=True) for li in cons_section.find_all('li')]

        return pros, cons

    async def scrape_stock(self, symbol: str) -> StockData:
        html = await self.fetch_html(symbol)
        soup = BeautifulSoup(html, 'lxml')

        # Extract Company Name
        company_name_tag = soup.find('h1')
        company_name = company_name_tag.get_text(strip=True) if company_name_tag else symbol

        # Extract About
        about = ""
        # Try multiple selectors for robustness
        about_div = (
            soup.find('div', class_='company-profile-about') or
            soup.find('div', id='company-profile') or
            soup.find('div', class_='about')
        )
        if about_div:
            # Usually parsing the text inside p
            p_tag = about_div.find('p')
            if p_tag:
                 about = p_tag.get_text(strip=True)
            else:
                 about = about_div.get_text(strip=True)

        # Header
        header = self._parse_header(soup)

        # Pros & Cons
        pros, cons = self._parse_pros_cons(soup)

        # Tables
        quarterly_results = self._extract_table(soup, 'quarters')
        profit_loss = self._extract_table(soup, 'profit-loss')
        balance_sheet = self._extract_table(soup, 'balance-sheet')
        cash_flow = self._extract_table(soup, 'cash-flow')
        ratios = self._extract_table(soup, 'ratios')
        shareholding = self._extract_table(soup, 'shareholding')

        # Peers - Fetch dynamically
        peers = []
        # Find company ID
        # <div data-company-id="1298" id="company-info"></div>
        company_info = soup.find('div', id='company-info')
        if company_info and company_info.has_attr('data-company-id'):
            company_id = company_info['data-company-id']
            peers = await self.fetch_peers(company_id)

        # Documents
        documents = self._parse_documents(soup)

        return StockData(
            symbol=symbol,
            company_name=company_name,
            header=header,
            about=about,
            pros=pros,
            cons=cons,
            quarterly_results=quarterly_results,
            profit_loss=profit_loss,
            balance_sheet=balance_sheet,
            cash_flow=cash_flow,
            ratios=ratios,
            shareholding_pattern=shareholding,
            peers=peers,
            documents=documents
        )

if __name__ == "__main__":
    import json

    async def main():
        scraper = ScreenerScraper()
        symbol = "HDFCBANK"
        print(f"Testing fetch for {symbol}...")
        try:
            data = await scraper.scrape_stock(symbol)
            print("Successfully fetched data.")
            print(json.dumps(data.model_dump(), indent=2))
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(main())
