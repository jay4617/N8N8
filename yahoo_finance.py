#!/usr/bin/env python3
"""
Yahoo Finance integration for real-time market data.
"""

import yfinance as yf
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)

class YahooFinanceService:
    """Service for fetching real-time market data using Yahoo Finance API."""
    
    def __init__(self):
        self.session = None
        
    def get_stock_info(self, symbol: str) -> Dict:
        """Get comprehensive stock information."""
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            # Get current price and basic metrics
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            
            result = {
                'symbol': symbol.upper(),
                'company_name': info.get('longName', info.get('shortName', 'N/A')),
                'current_price': current_price,
                'currency': info.get('currency', 'USD'),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'volume': info.get('volume', 0),
                'avg_volume': info.get('averageVolume', 0),
                'day_high': info.get('dayHigh', 0),
                'day_low': info.get('dayLow', 0),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                'beta': info.get('beta', 0),
                'eps': info.get('trailingEps', 0),
                'revenue': info.get('totalRevenue', 0),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'exchange': info.get('exchange', 'N/A'),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching stock info for {symbol}: {e}")
            return {'error': f"Could not fetch data for {symbol}"}
    
    def get_price_only(self, symbol: str) -> Dict:
        """Get just the current price for quick queries."""
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            change = info.get('regularMarketChange', 0)
            change_percent = info.get('regularMarketChangePercent', 0)
            
            return {
                'symbol': symbol.upper(),
                'price': current_price,
                'change': change,
                'change_percent': change_percent * 100 if change_percent else 0,
                'currency': info.get('currency', 'USD'),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return {'error': f"Could not fetch price for {symbol}"}
    
    def get_historical_data(self, symbol: str, period: str = "1mo") -> Dict:
        """Get historical price data."""
        try:
            ticker = yf.Ticker(symbol.upper())
            
            # Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            hist = ticker.history(period=period)
            
            if hist.empty:
                return {'error': f"No historical data found for {symbol}"}
            
            # Get recent data points
            recent = hist.tail(5)
            
            result = {
                'symbol': symbol.upper(),
                'period': period,
                'data_points': len(hist),
                'latest_close': float(hist['Close'].iloc[-1]),
                'latest_volume': int(hist['Volume'].iloc[-1]),
                'period_high': float(hist['High'].max()),
                'period_low': float(hist['Low'].min()),
                'period_start': hist.index[0].strftime('%Y-%m-%d'),
                'period_end': hist.index[-1].strftime('%Y-%m-%d'),
                'recent_prices': [
                    {
                        'date': date.strftime('%Y-%m-%d'),
                        'close': float(row['Close']),
                        'volume': int(row['Volume'])
                    }
                    for date, row in recent.iterrows()
                ],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return {'error': f"Could not fetch historical data for {symbol}"}
    
    def get_multiple_quotes(self, symbols: List[str]) -> Dict:
        """Get current prices for multiple symbols."""
        try:
            symbols_str = ' '.join([s.upper() for s in symbols])
            tickers = yf.Tickers(symbols_str)
            
            results = {}
            for symbol in symbols:
                try:
                    ticker = tickers.tickers[symbol.upper()]
                    info = ticker.info
                    
                    current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                    change_percent = info.get('regularMarketChangePercent', 0)
                    
                    results[symbol.upper()] = {
                        'price': current_price,
                        'change_percent': change_percent * 100 if change_percent else 0,
                        'currency': info.get('currency', 'USD')
                    }
                except:
                    results[symbol.upper()] = {'error': 'Data not available'}
            
            results['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return results
            
        except Exception as e:
            logger.error(f"Error fetching multiple quotes: {e}")
            return {'error': 'Could not fetch multiple quotes'}
    
    def get_market_summary(self) -> Dict:
        """Get major market indices summary."""
        try:
            indices = {
                'S&P 500': '^GSPC',
                'Dow Jones': '^DJI', 
                'NASDAQ': '^IXIC',
                'Russell 2000': '^RUT',
                'VIX': '^VIX'
            }
            
            summary = {}
            for name, symbol in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    
                    current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                    change = info.get('regularMarketChange', 0)
                    change_percent = info.get('regularMarketChangePercent', 0)
                    
                    summary[name] = {
                        'symbol': symbol,
                        'price': current_price,
                        'change': change,
                        'change_percent': change_percent * 100 if change_percent else 0
                    }
                except:
                    summary[name] = {'error': 'Data not available'}
            
            summary['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return summary
            
        except Exception as e:
            logger.error(f"Error fetching market summary: {e}")
            return {'error': 'Could not fetch market summary'}
    
    def search_symbol(self, query: str) -> Dict:
        """Search for stock symbols by company name."""
        try:
            # This is a basic implementation - yfinance doesn't have built-in search
            # We'll try common variations
            common_symbols = {
                'apple': 'AAPL',
                'microsoft': 'MSFT', 
                'google': 'GOOGL',
                'alphabet': 'GOOGL',
                'amazon': 'AMZN',
                'tesla': 'TSLA',
                'facebook': 'META',
                'meta': 'META',
                'netflix': 'NFLX',
                'nvidia': 'NVDA',
                'berkshire': 'BRK-B',
                'warren buffett': 'BRK-B',
                'jp morgan': 'JPM',
                'jpmorgan': 'JPM',
                'goldman sachs': 'GS',
                'morgan stanley': 'MS',
                'coca cola': 'KO',
                'pepsi': 'PEP',
                'walmart': 'WMT',
                'disney': 'DIS'
            }
            
            query_lower = query.lower()
            if query_lower in common_symbols:
                symbol = common_symbols[query_lower]
                return {
                    'query': query,
                    'found_symbol': symbol,
                    'suggestion': f"Did you mean {symbol}?"
                }
            
            # If not found, suggest trying the query as-is
            return {
                'query': query,
                'suggestion': f"Try using the exact ticker symbol (e.g., AAPL for Apple)"
            }
            
        except Exception as e:
            logger.error(f"Error searching symbol for {query}: {e}")
            return {'error': f"Could not search for {query}"}

# Global instance
yahoo_finance = YahooFinanceService()

def format_stock_data_for_bot(data: Dict) -> str:
    """Format stock data for bot responses."""
    if 'error' in data:
        return f"❌ {data['error']}"
    
    if 'price' in data and 'symbol' in data:
        # Price-only format
        change_emoji = "📈" if data.get('change_percent', 0) >= 0 else "📉"
        return f"💰 **{data['symbol']}**: ${data['price']:.2f} {change_emoji} {data.get('change_percent', 0):.2f}%"
    
    if 'company_name' in data:
        # Full stock info format
        price = data.get('current_price', 0)
        pe = data.get('pe_ratio', 0)
        div_yield = data.get('dividend_yield', 0)
        beta = data.get('beta', 0)
        
        pe_str = f"{pe:.2f}" if pe else 'N/A'
        div_str = f"{div_yield*100:.2f}%" if div_yield else 'N/A'
        beta_str = f"{beta:.2f}" if beta else 'N/A'
        
        response = f"""📊 **{data['company_name']} ({data['symbol']})**
💰 Price: ${price:.2f} ({data.get('currency', 'USD')})
📈 P/E Ratio: {pe_str}
💵 Dividend Yield: {div_str}
⚡ Beta: {beta_str}
🏢 Sector: {data.get('sector', 'N/A')}
📅 Data as of: {data.get('timestamp', 'N/A')}"""
        
        return response
    
    return "📊 Market data retrieved successfully"

def format_market_summary_for_bot(data: Dict) -> str:
    """Format market summary for bot responses."""
    if 'error' in data:
        return f"❌ {data['error']}"
    
    response = "📈 **Market Summary**\n\n"
    
    for name, info in data.items():
        if name == 'timestamp':
            continue
            
        if 'error' in info:
            response += f"❌ {name}: Data unavailable\n"
        else:
            change_emoji = "📈" if info.get('change_percent', 0) >= 0 else "📉"
            response += f"{change_emoji} **{name}**: {info.get('price', 0):.2f} ({info.get('change_percent', 0):+.2f}%)\n"
    
    response += f"\n📅 As of: {data.get('timestamp', 'N/A')}"
    return response