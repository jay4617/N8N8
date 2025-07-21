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
    
    async def generate(self, question: str, context: str = ""):
        try:
            if context:
                prompt = f"""You are a finance expert. Use this knowledge to answer ONLY finance questions: {context}

Question: {question}

STRICT RULES:
- If the question is about finance/investing/trading/economics: Answer using the knowledge provided
- If the question is NOT about finance (restaurants, travel, personal questions, AI/tech questions): Reply EXACTLY with: "I'm sorry, but I specialize in quantitative finance and can only help with finance-related questions. I can assist you with portfolio optimization, risk management, derivatives pricing, trading strategies, and financial modeling. Please ask me a finance-related question!"
- NEVER mention: books, chapters, authors, documents, context, data sources, AI models, Moonshot, Kimi, or any technical details
- NEVER provide restaurant recommendations, travel advice, or general information
- Sound like a human finance expert, not an AI system

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
                "model": "moonshotai/kimi-k2",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.7
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

I'm your Finance assistant. I can help you with:

📈 Portfolio Theory & Optimization
📊 Risk Management & Analysis  
💱 Derivatives & Financial Instruments
📉 Market Analysis & Trading Strategies
🔢 Mathematical Finance & Models

Ask me any quantitative finance question to get started!"""
        
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
        
        # Search for context
        context_docs = vector_db.search(question, n_results=3)
        context_text = ""
        if context_docs:
            context_text = "\n\n".join(context_docs[:2])  # Use top 2 results
            if len(context_text) > 3000:  # Limit context length
                context_text = context_text[:3000] + "..."
        
        # Generate response
        answer = await llm.generate(question, context_text)
        
        # Send response
        await update.message.reply_text(answer)
        logger.info(f"✅ Answered {user}")
        
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