#!/usr/bin/env python3
"""
Financial Modeling Prep API Service
Provides M&A RSS Feed and Company Search functionality.
"""

import logging
import aiohttp
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class FMPService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api"
        self.session = None
        
    async def _get_session(self):
        """Get or create aiohttp session."""
        if not self.session:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request to FMP."""
        try:
            if not params:
                params = {}
            params['apikey'] = self.api_key
            
            session = await self._get_session()
            url = f"{self.base_url}/{endpoint}"
            
            logger.info(f"Making FMP API request to: {url}")
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"FMP API success: {len(data) if isinstance(data, list) else 'object'} items")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"FMP API error {response.status}: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"FMP API request error: {e}")
            return None
    
    async def get_ma_rss_feed(self, page: int = 0) -> Optional[List[Dict]]:
        """Get M&A RSS feed from FMP."""
        endpoint = f"v4/mergers-acquisitions-rss-feed"
        params = {"page": page}
        
        data = await self._make_request(endpoint, params)
        return data if isinstance(data, list) else None
    
    async def search_company(self, query: str) -> Optional[List[Dict]]:
        """Search for companies using FMP general search."""
        endpoint = f"v3/search"
        params = {"query": query}
        
        data = await self._make_request(endpoint, params)
        return data if isinstance(data, list) else None
    
    async def get_stock_quote(self, symbol: str) -> Optional[Dict]:
        """Get real-time stock quote for a symbol."""
        endpoint = f"v3/quote/{symbol.upper()}"
        
        data = await self._make_request(endpoint)
        return data[0] if isinstance(data, list) and len(data) > 0 else None
    
    async def get_company_profile(self, symbol: str) -> Optional[Dict]:
        """Get company profile information."""
        endpoint = f"v3/profile/{symbol.upper()}"
        
        data = await self._make_request(endpoint)
        return data[0] if isinstance(data, list) and len(data) > 0 else None
    
    async def get_historical_data(self, symbol: str, limit: int = 5) -> Optional[Dict]:
        """Get historical price data for a symbol."""
        endpoint = f"v3/historical-price-full/{symbol.upper()}"
        params = {"limit": limit}
        
        data = await self._make_request(endpoint, params)
        return data if isinstance(data, dict) else None
    
    async def format_ma_feed(self, ma_data: List[Dict], limit: int = 5) -> str:
        """Format M&A RSS feed data for display."""
        if not ma_data:
            return "❌ No M&A data available at the moment."
        
        formatted = "🤝 **Latest Mergers & Acquisitions**\n\n"
        
        for i, item in enumerate(ma_data[:limit]):
            try:
                title = item.get('title', 'N/A')
                link = item.get('link', '')
                pub_date = item.get('pubDate', '')
                description = item.get('description', '')
                
                # Clean and truncate description
                if description and len(description) > 150:
                    description = description[:150] + "..."
                
                formatted += f"**{i+1}. {title}**\n"
                if description:
                    formatted += f"📝 {description}\n"
                if pub_date:
                    formatted += f"📅 {pub_date}\n"
                if link:
                    formatted += f"🔗 [Read More]({link})\n"
                formatted += "\n"
                
            except Exception as e:
                logger.error(f"Error formatting M&A item: {e}")
                continue
        
        return formatted
    
    async def format_company_search(self, search_data: List[Dict], limit: int = 8) -> str:
        """Format company search results for display."""
        if not search_data:
            return "❌ No companies found matching your search."
        
        formatted = "🔍 **Company Search Results**\n\n"
        
        for i, company in enumerate(search_data[:limit]):
            try:
                symbol = company.get('symbol', 'N/A')
                name = company.get('name', 'N/A')
                currency = company.get('currency', '')
                stock_exchange = company.get('stockExchange', '')
                exchange_short = company.get('exchangeShortName', '')
                
                formatted += f"**{i+1}. {name}** ({symbol})\n"
                
                if exchange_short:
                    formatted += f"📈 Exchange: {exchange_short}"
                    if stock_exchange and stock_exchange != exchange_short:
                        formatted += f" ({stock_exchange})"
                    formatted += "\n"
                
                if currency:
                    formatted += f"💱 Currency: {currency}\n"
                
                formatted += "\n"
                
            except Exception as e:
                logger.error(f"Error formatting company item: {e}")
                continue
        
        return formatted
    
    async def format_stock_quote(self, quote_data: Dict) -> str:
        """Format stock quote data for display."""
        try:
            symbol = quote_data.get('symbol', 'N/A')
            name = quote_data.get('name', 'N/A') 
            price = quote_data.get('price', 0)
            change = quote_data.get('change', 0)
            change_percent = quote_data.get('changesPercentage', 0)
            day_low = quote_data.get('dayLow', 0)
            day_high = quote_data.get('dayHigh', 0)
            year_low = quote_data.get('yearLow', 0)
            year_high = quote_data.get('yearHigh', 0)
            volume = quote_data.get('volume', 0)
            market_cap = quote_data.get('marketCap', 0)
            
            # Format change indicator
            change_indicator = "🟢" if change >= 0 else "🔴"
            change_sign = "+" if change >= 0 else ""
            
            formatted = f"📈 **{name} ({symbol})**\n\n"
            formatted += f"💰 **Current Price**: ${price:.2f}\n"
            formatted += f"{change_indicator} **Change**: {change_sign}${change:.2f} ({change_sign}{change_percent:.2f}%)\n\n"
            
            formatted += f"📊 **Today's Range**: ${day_low:.2f} - ${day_high:.2f}\n"
            formatted += f"📈 **52 Week Range**: ${year_low:.2f} - ${year_high:.2f}\n"
            
            if volume > 0:
                formatted += f"📦 **Volume**: {volume:,}\n"
            
            if market_cap > 0:
                market_cap_b = market_cap / 1e9
                formatted += f"🏢 **Market Cap**: ${market_cap_b:.2f}B\n"
                
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting stock quote: {e}")
            return "❌ Error formatting stock data."
    
    async def format_company_profile(self, profile_data: Dict) -> str:
        """Format company profile data for display."""
        try:
            symbol = profile_data.get('symbol', 'N/A')
            company_name = profile_data.get('companyName', 'N/A')
            price = profile_data.get('price', 0)
            industry = profile_data.get('industry', 'N/A')
            sector = profile_data.get('sector', 'N/A')
            website = profile_data.get('website', '')
            description = profile_data.get('description', '')
            ceo = profile_data.get('ceo', '')
            employees = profile_data.get('fullTimeEmployees', 0)
            
            formatted = f"🏢 **{company_name} ({symbol})**\n\n"
            formatted += f"💰 **Current Price**: ${price:.2f}\n"
            formatted += f"🏭 **Industry**: {industry}\n"
            formatted += f"📊 **Sector**: {sector}\n"
            
            if ceo:
                formatted += f"👨‍💼 **CEO**: {ceo}\n"
                
            if employees > 0:
                formatted += f"👥 **Employees**: {employees:,}\n"
            
            if website:
                formatted += f"🌐 **Website**: {website}\n"
                
            if description and isinstance(description, str) and len(description) > 0:
                desc_short = description[:300] + "..." if len(description) > 300 else description
                formatted += f"\n📝 **About**:\n{desc_short}\n"
                
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting company profile: {e}")
            return "❌ Error formatting company profile."
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

# Global FMP service instance
fmp_service = FMPService("XI4MJ7aH5tnaa1cZ7gOmaoTJK4h9VhUj")

# Convenience functions for bot integration
async def get_ma_feed_response(page: int = 0) -> str:
    """Get formatted M&A RSS feed response."""
    try:
        ma_data = await fmp_service.get_ma_rss_feed(page)
        return await fmp_service.format_ma_feed(ma_data)
    except Exception as e:
        logger.error(f"Error getting M&A feed: {e}")
        return "❌ Unable to fetch M&A data at the moment. Please try again later."

async def get_company_search_response(query: str) -> str:
    """Get formatted company search response."""
    try:
        search_data = await fmp_service.search_company(query)
        return await fmp_service.format_company_search(search_data)
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        return "❌ Unable to search companies at the moment. Please try again later."

async def get_stock_quote_response(symbol: str) -> str:
    """Get formatted stock quote response."""
    try:
        quote_data = await fmp_service.get_stock_quote(symbol)
        if quote_data:
            return await fmp_service.format_stock_quote(quote_data)
        else:
            return f"❌ No quote data found for symbol {symbol.upper()}. Try searching for the company first."
    except Exception as e:
        logger.error(f"Error getting stock quote: {e}")
        return "❌ Unable to fetch stock quote at the moment. Please try again later."

async def get_company_profile_response(symbol: str) -> str:
    """Get formatted company profile response."""
    try:
        profile_data = await fmp_service.get_company_profile(symbol)
        if profile_data:
            return await fmp_service.format_company_profile(profile_data)
        else:
            return f"❌ No profile data found for symbol {symbol.upper()}. Try searching for the company first."
    except Exception as e:
        logger.error(f"Error getting company profile: {e}")
        return "❌ Unable to fetch company profile at the moment. Please try again later."

# Test function
async def test_fmp_api():
    """Test FMP API endpoints."""
    print("🧪 Testing Financial Modeling Prep API...")
    
    # Test Company Search
    print("\n🔍 Testing Company Search (query: 'Apple')...")
    search_response = await get_company_search_response("Apple")
    print(search_response[:300] + "..." if len(search_response) > 300 else search_response)
    
    # Test Stock Quote
    print("\n📈 Testing Stock Quote (AAPL)...")
    quote_response = await get_stock_quote_response("AAPL")
    print(quote_response[:400] + "..." if len(quote_response) > 400 else quote_response)
    
    # Test Company Profile
    print("\n🏢 Testing Company Profile (TSLA)...")
    profile_response = await get_company_profile_response("TSLA")
    print(profile_response[:400] + "..." if len(profile_response) > 400 else profile_response)
    
    # Clean up
    await fmp_service.close()
    print("\n✅ FMP API test completed!")

if __name__ == "__main__":
    asyncio.run(test_fmp_api())