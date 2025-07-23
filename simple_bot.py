#!/usr/bin/env python3
"""
Clean working bot without complex dependencies causing exceptions.
"""

import logging
import sys
import asyncio
import aiohttp
import json
from datetime import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import Config
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from pathlib import Path
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage
from langchain_community.chat_message_histories import FileChatMessageHistory
import pickle
import os
import re
<<<<<<< HEAD
from yahoo_finance import yahoo_finance, format_stock_data_for_bot, format_market_summary_for_bot
=======
import time
from fmp_service import get_ma_feed_response, get_company_search_response, get_stock_quote_response, get_company_profile_response
>>>>>>> 1e6e3ce (Update)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class SimpleVectorDB:
    def __init__(self):
        self.db_path = Path("./chroma_db")
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize with minimal settings to avoid telemetry issues
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get collection
        try:
            self.collection = self.client.get_collection("documents")
            logger.info("Loaded existing document collection")
        except:
            logger.info("No existing collection found")
            self.collection = None
    
    def search(self, query: str, n_results: int = 3):
        if not self.collection:
            return []
        
        try:
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents']
            )
            return results['documents'][0] if results['documents'] else []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

class SimpleLLM:
    def __init__(self):
        self.api_key = Config.DEEPSEEK_API_KEY
        self.base_url = Config.DEEPSEEK_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
<<<<<<< HEAD
=======
        # Rate limiting removed for better user experience
>>>>>>> 1e6e3ce (Update)
    
    async def generate(self, question: str, context: str = "", conversation_history: str = ""):
        try:
            # Build comprehensive context including conversation history
            full_context = ""
            if conversation_history:
                full_context += f"Previous conversation:\n{conversation_history}\n\n"
            if context:
                full_context += f"Knowledge base: {context}"
            
            if full_context:
                prompt = f"""You are a finance expert. Use this information to answer finance questions and provide follow-up responses based on conversation history.

{full_context}

Current question: {question}

STRICT RULES:
- If the question is about finance/investing/trading/economics: Answer using the knowledge and conversation history
- Consider previous questions for context (e.g., if user asked about stocks earlier, "this stock" refers to that context)
- If the question is NOT about finance (restaurants, travel, personal questions, AI/tech questions): Reply EXACTLY with: "I'm sorry, but I specialize in quantitative finance and can only help with finance-related questions. I can assist you with portfolio optimization, risk management, derivatives pricing, trading strategies, and financial modeling. Please ask me a finance-related question!"
- NEVER mention: books, chapters, authors, documents, context, data sources, AI models, Moonshot, Kimi, or any technical details
- NEVER provide restaurant recommendations, travel advice, or general information
- Sound like a human finance expert with memory of the conversation

Answer:"""
            else:
                prompt = f"""You are a finance expert. 

Question: {question}

STRICT RULES:
- If about finance/investing/trading/economics: Provide expert knowledge
- If NOT about finance: Reply EXACTLY with: "I'm sorry, but I specialize in quantitative finance and can only help with finance-related questions. I can assist you with portfolio optimization, risk management, derivatives pricing, trading strategies, and financial modeling. Please ask me a finance-related question!"
- NEVER mention AI models, Moonshot, Kimi, or any technical information
- NEVER provide non-finance information like restaurants, travel, etc.

Answer:"""
            
            payload = {
<<<<<<< HEAD
                "model": "moonshotai/kimi-k2",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.7
=======
                "model": Config.MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "You are an expert in quantitative finance and trading."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": Config.MAX_TOKENS,
                "temperature": Config.TEMPERATURE,
                "top_p": Config.TOP_P
>>>>>>> 1e6e3ce (Update)
            }
            
            # Create SSL context that doesn't verify certificates
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "choices" in result and result["choices"]:
                            return result["choices"][0]["message"]["content"].strip()
                    else:
                        error_text = await response.text()
                        logger.error(f"API error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"LLM error: {e}")
        
        return "Sorry, I couldn't generate a response at the moment."

# Initialize services
vector_db = SimpleVectorDB()
llm = SimpleLLM()

# LangChain ConversationBufferMemory for each user
user_memories = {}

def get_user_memory(user_id: int) -> ConversationBufferMemory:
    """Get or create ConversationBufferMemory for a user with optional persistence."""
    if user_id not in user_memories:
        # Create memory directory if it doesn't exist
        memory_dir = Path("./user_memories")
        memory_dir.mkdir(exist_ok=True)
        
        # Create memory with file-based chat history for persistence
        memory_file = memory_dir / f"user_{user_id}_memory.json"
        chat_history = FileChatMessageHistory(file_path=str(memory_file))
        
        user_memories[user_id] = ConversationBufferMemory(
            chat_memory=chat_history,
            return_messages=True,
            memory_key="chat_history"
        )
    return user_memories[user_id]

def add_to_conversation_memory(user_id: int, user_message: str, bot_response: str):
    """Add message pair to user's LangChain memory."""
    memory = get_user_memory(user_id)
    memory.chat_memory.add_user_message(user_message)
    memory.chat_memory.add_ai_message(bot_response)

def get_conversation_context(user_id: int) -> str:
    """Get recent conversation history from LangChain memory."""
    memory = get_user_memory(user_id)
    messages = memory.chat_memory.messages
    
    if not messages:
        return ""
    
    # Format recent messages for context (last 6 messages = 3 exchanges)
    context_parts = []
    recent_messages = messages[-6:] if len(messages) > 6 else messages
    
    for i in range(0, len(recent_messages), 2):
        if i + 1 < len(recent_messages):
            human_msg = recent_messages[i]
            ai_msg = recent_messages[i + 1]
            context_parts.append(f"User previously asked: {human_msg.content}")
            # Truncate AI response for context length
            ai_content = ai_msg.content[:200] + "..." if len(ai_msg.content) > 200 else ai_msg.content
            context_parts.append(f"You responded: {ai_content}")
    
    return "\n".join(context_parts)

<<<<<<< HEAD
# Stock query detection and handling
def detect_stock_query(message: str) -> dict:
    """Detect if message is asking for stock information and extract symbols."""
    message_lower = message.lower()
    
    # Market summary queries
    market_queries = [
        'market summary', 'market overview', 'indices', 'dow jones', 'nasdaq', 's&p 500', 'sp500', 'market indices'
    ]
    
    # Check for market summary request
    for query in market_queries:
        if query in message_lower:
            return {'type': 'market_summary'}
    
    # Check for common company names first (more specific)
    company_patterns = {
        r'\bapple\b': 'AAPL',
        r'\bmicrosoft\b': 'MSFT',
        r'\bgoogle\b': 'GOOGL',
        r'\bamazon\b': 'AMZN',
        r'\btesla\b': 'TSLA',
        r'\bmeta\b|facebook': 'META',
        r'\bnvidia\b': 'NVDA',
        r'\bberkshire\b': 'BRK-B',
    }
    
    symbols = []
    for pattern, symbol in company_patterns.items():
        if re.search(pattern, message_lower):
            symbols.append(symbol)
    
    # Look for explicit stock symbols (2-5 uppercase letters)
    # More restrictive patterns
    if 'price' in message_lower or 'quote' in message_lower or 'stock' in message_lower:
        # Extract stock symbols only when price/quote/stock keywords are present
        stock_patterns = [
            r'\b([A-Z]{2,5})\b(?:\s+(?:stock|price|quote|share)|\s*(?:stock|price|quote|share))',
            r'(?:price|quote|stock|share)\s+(?:of\s+)?([A-Z]{2,5})\b',
            r'\$([A-Z]{2,5})\b',
        ]
        
        for pattern in stock_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2 and len(match) <= 5 and match.isalpha():
                    symbols.append(match.upper())
    
    # Remove duplicates and common false positives
    symbols = list(set(symbols))
    false_positives = ['WHAT', 'THE', 'PRICE', 'OF', 'SHOW', 'ME', 'GET', 'IS', 'ARE', 'CAN', 'YOU', 'GIVE']
    symbols = [s for s in symbols if s not in false_positives]
    
    if symbols:
        return {'type': 'stock_quote', 'symbols': symbols}
    
    return {'type': 'none'}

def get_stock_data_response(query_result: dict) -> str:
    """Get formatted stock data based on query type."""
    try:
        if query_result['type'] == 'market_summary':
            data = yahoo_finance.get_market_summary()
            return format_market_summary_for_bot(data)
        
        elif query_result['type'] == 'stock_quote':
            symbols = query_result['symbols']
            
            if len(symbols) == 1:
                # Single stock - get detailed info
                data = yahoo_finance.get_stock_info(symbols[0])
                return format_stock_data_for_bot(data)
            
            elif len(symbols) <= 5:
                # Multiple stocks - get price summary
                data = yahoo_finance.get_multiple_quotes(symbols)
                response = "📊 **Stock Prices**\n\n"
                
                for symbol, info in data.items():
                    if symbol == 'timestamp':
                        continue
                    if 'error' in info:
                        response += f"❌ {symbol}: Data unavailable\n"
                    else:
                        change_emoji = "📈" if info.get('change_percent', 0) >= 0 else "📉"
                        response += f"{change_emoji} **{symbol}**: ${info.get('price', 0):.2f} ({info.get('change_percent', 0):+.2f}%)\n"
                
                response += f"\n📅 As of: {data.get('timestamp', 'N/A')}"
                return response
            
            else:
                return "❌ Too many symbols requested. Please ask for 5 or fewer stocks at once."
    
    except Exception as e:
        logger.error(f"Error getting stock data: {e}")
        return "❌ Sorry, I couldn't fetch the market data right now. Please try again."
    
    return "❌ Could not process your stock query."
=======
# Query detection for FMP API features
def detect_fmp_query(message: str) -> dict:
    """Detect FMP API queries (M&A feed, company search, stock quotes, profiles)."""
    message_lower = message.lower()
    
    # M&A related keywords
    ma_keywords = [
        'merger', 'mergers', 'acquisition', 'acquisitions', 'm&a', 'ma', 
        'takeover', 'buyout', 'merge', 'acquired', 'deal', 'deals'
    ]
    
    # Check for M&A queries
    if any(keyword in message_lower for keyword in ma_keywords):
        return {'type': 'ma_feed'}
    
    # Company search keywords
    search_keywords = [
        'search', 'find', 'look up', 'lookup', 'company', 'companies'
    ]
    
    # Check for company search patterns
    if any(keyword in message_lower for keyword in search_keywords):
        search_patterns = [
            r'search(?:\s+for)?\s+([A-Za-z0-9\s&.,-]+)',
            r'find(?:\s+company)?\s+([A-Za-z0-9\s&.,-]+)',
            r'look\s*up\s+([A-Za-z0-9\s&.,-]+)',
            r'company\s+([A-Za-z0-9\s&.,-]+)',
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, message_lower)
            if match:
                query = match.group(1).strip()
                if len(query) >= 1:
                    return {'type': 'company_search', 'query': query}
    
    # Stock quote patterns - look for specific symbols or price requests
    quote_patterns = [
        r'\$([A-Z]{2,5})\b',  # $AAPL
        r'\b([A-Z]{2,5})\s+(?:price|quote|stock)\b',  # AAPL price
        r'(?:price|quote)\s+(?:of\s+)?([A-Z]{2,5})\b',  # price of AAPL
        r'what\s+is\s+([A-Z]{2,5})\s+(?:price|stock|quote)',  # what is AAPL price
    ]
    
    for pattern in quote_patterns:
        match = re.search(pattern, message)
        if match:
            symbol = match.group(1).upper()
            if len(symbol) >= 2 and len(symbol) <= 5:
                return {'type': 'stock_quote', 'symbol': symbol}
    
    # Company profile patterns - look for "about" or "info" requests
    profile_patterns = [
        r'(?:about|info|profile|tell\s+me\s+about)\s+([A-Z]{2,5})\b',
        r'([A-Z]{2,5})\s+(?:info|profile|company|about)',
    ]
    
    for pattern in profile_patterns:
        match = re.search(pattern, message)
        if match:
            symbol = match.group(1).upper()
            if len(symbol) >= 2 and len(symbol) <= 5:
                return {'type': 'company_profile', 'symbol': symbol}
    
    # General stock-related queries (for known company names)
    stock_company_patterns = {
        r'\bapple\s+(?:stock|price|quote)': 'AAPL',
        r'\bmicrosoft\s+(?:stock|price|quote)': 'MSFT', 
        r'\bgoogle\s+(?:stock|price|quote)': 'GOOGL',
        r'\bamazon\s+(?:stock|price|quote)': 'AMZN',
        r'\btesla\s+(?:stock|price|quote)': 'TSLA',
        r'\bmeta\s+(?:stock|price|quote)': 'META',
        r'\bnvidia\s+(?:stock|price|quote)': 'NVDA',
    }
    
    for pattern, symbol in stock_company_patterns.items():
        if re.search(pattern, message_lower):
            return {'type': 'stock_quote', 'symbol': symbol}
    
    return {'type': 'none'}


async def get_fmp_response(query_result: dict) -> str:
    """Handle FMP API queries."""
    query_type = query_result.get('type', 'none')
    
    if query_type == 'ma_feed':
        logger.info("🤝 Fetching M&A RSS feed...")
        return await get_ma_feed_response()
    
    elif query_type == 'company_search':
        search_query = query_result.get('query', '')
        logger.info(f"🔍 Searching companies for: {search_query}")
        return await get_company_search_response(search_query)
    
    elif query_type == 'stock_quote':
        symbol = query_result.get('symbol', '')
        logger.info(f"📈 Getting stock quote for: {symbol}")
        return await get_stock_quote_response(symbol)
    
    elif query_type == 'company_profile':
        symbol = query_result.get('symbol', '')
        logger.info(f"🏢 Getting company profile for: {symbol}")
        return await get_company_profile_response(symbol)
    
    return "❌ Query type not recognized."
>>>>>>> 1e6e3ce (Update)

# User query logging
def log_user_query(user_name: str, user_id: int, message: str, message_type: str = "question"):
    """Log user queries to a text file with immediate flush."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message_type.upper()} | User: {user_name} (ID: {user_id}) | Message: {message}\n"
        
        with open("user_queries.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)
            f.flush()  # Force immediate write to disk
        
        # Also print to console for real-time monitoring
        print(f"📝 LOGGED: {log_entry.strip()}")
        
    except Exception as e:
        logger.error(f"Error logging user query: {e}")

def log_bot_response(user_name: str, user_id: int, response: str):
    """Log COMPLETE bot responses to the same file with immediate flush."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Log the FULL response without truncation
        log_entry = f"[{timestamp}] RESPONSE | To: {user_name} (ID: {user_id}) | Full Response:\n{response}\n"
        log_entry += "="*80 + "\n"  # Separator line
        
        with open("user_queries.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)
            f.flush()  # Force immediate write to disk
        
        # Also print to console for real-time monitoring (with preview)
        response_preview = response[:100] + "..." if len(response) > 100 else response
        print(f"🤖 LOGGED: Response sent to {user_name} - {response_preview}")
        
    except Exception as e:
        logger.error(f"Error logging bot response: {e}")

async def start_handler(update, context):
    """Handle /start command."""
    try:
        user = update.effective_user.first_name or "User"
        user_id = update.effective_user.id
        logger.info(f"📝 /start from {user}")
        
        # Log the /start command
        log_user_query(user, user_id, "/start", "command")
        
        response = f"""🤖 Welcome {user}!

I'm your AI Finance assistant. I can help you with:

📈 Portfolio Theory & Optimization
📊 Risk Management & Analysis  
💱 Derivatives & Financial Instruments
📉 Market Analysis & Trading Strategies
🔢 Mathematical Finance & Models
💰 Real-time Stock Prices & Market Data

**Examples:**
<<<<<<< HEAD
• "What is Apple stock price?" 
• "Show me market summary"
• "Explain portfolio diversification"
• "TSLA quote"
=======
• "Show me latest mergers and acquisitions"
• "Search for Apple company"
• "Explain portfolio diversification"
• "What are options trading strategies?"
>>>>>>> 1e6e3ce (Update)

Ask me any finance question to get started!"""
        
        await update.message.reply_text(response)
        logger.info(f"✅ Sent /start response to {user}")
        
        # Log the bot response
        log_bot_response(user, user_id, response)
        
    except Exception as e:
        logger.error(f"❌ Start error: {e}")
        await update.message.reply_text("Welcome! Ask me any quantitative finance question.")

async def question_handler(update, context):
    """Handle questions."""
    try:
        user = update.effective_user.first_name or "User"
        user_id = update.effective_user.id
        question = update.message.text
        
        logger.info(f"📝 Question from {user}: {question}")
        
        # Log the user question
        log_user_query(user, user_id, question, "question")
        
        # Show typing
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
<<<<<<< HEAD
        # Check if this is a stock query first
        stock_query = detect_stock_query(question)
        
        if stock_query['type'] != 'none':
            # Handle stock data request
            logger.info(f"📊 Stock query detected: {stock_query}")
            answer = get_stock_data_response(stock_query)
            
            # Send stock data response
            await update.message.reply_text(answer, parse_mode='Markdown')
            logger.info(f"✅ Sent stock data to {user}")
=======
        # Check if this is an FMP API query first
        fmp_query = detect_fmp_query(question)
        
        if fmp_query['type'] != 'none':
            # Handle FMP API request (M&A, company search, or stock maintenance)
            logger.info(f"📊 FMP query detected: {fmp_query['type']}")
            answer = await get_fmp_response(fmp_query)
            
            # Send FMP response
            await update.message.reply_text(answer, parse_mode='Markdown')
            logger.info(f"✅ Sent FMP response to {user}")
>>>>>>> 1e6e3ce (Update)
            
        else:
            # Handle regular finance questions with RAG
            # Get conversation history for this user
            conversation_context = get_conversation_context(user_id)
            
            # Search for context
            context_docs = vector_db.search(question, n_results=3)
            context_text = ""
            if context_docs:
                context_text = "\n\n".join(context_docs[:2])  # Use top 2 results
                if len(context_text) > 3000:  # Limit context length
                    context_text = context_text[:3000] + "..."
            
            # Generate response with conversation memory
            answer = await llm.generate(question, context_text, conversation_context)
            
            # Send response
            await update.message.reply_text(answer)
            logger.info(f"✅ Answered {user}")
        
        # Add to conversation memory (both stock and regular responses)
        add_to_conversation_memory(user_id, question, answer)
        
        # Log the bot response
        log_bot_response(user, user_id, answer)
        
    except Exception as e:
        logger.error(f"❌ Question error: {e}")
        error_msg = "Sorry, I encountered an error. Please try again."
        await update.message.reply_text(error_msg)
        # Log the error response too
        log_bot_response(update.effective_user.first_name or "User", update.effective_user.id, error_msg)

def main():
    """Main function."""
    try:
        logger.info("🚀 Starting Simple RAG Bot...")
        
        # Create application
        app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, question_handler))
        
        logger.info("✅ Bot ready! Starting polling...")
        app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()