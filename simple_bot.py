#!/usr/bin/env python3
"""
Clean working bot without complex dependencies causing exceptions.
"""

import logging
import sys
import asyncio
import aiohttp
import json
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
                prompt = f"""You are an expert in quantitative finance. Answer based on this context:

Context: {context}

Question: {question}

Answer clearly and professionally:"""
            else:
                prompt = f"As a quantitative finance expert, answer: {question}"
            
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

async def start_handler(update, context):
    """Handle /start command."""
    try:
        user = update.effective_user.first_name or "User"
        logger.info(f"📝 /start from {user}")
        
        response = f"""🤖 Welcome {user}!

I'm your AI-powered Quantitative Finance assistant. I can help you with:

📈 Portfolio Theory & Optimization
📊 Risk Management & Analysis  
💱 Derivatives & Financial Instruments
📉 Market Analysis & Trading Strategies
🔢 Mathematical Finance & Models

Ask me any quantitative finance question to get started!"""
        
        await update.message.reply_text(response)
        logger.info(f"✅ Sent /start response to {user}")
        
    except Exception as e:
        logger.error(f"❌ Start error: {e}")
        await update.message.reply_text("Welcome! Ask me any quantitative finance question.")

async def question_handler(update, context):
    """Handle questions."""
    try:
        user = update.effective_user.first_name or "User"
        question = update.message.text
        
        logger.info(f"📝 Question from {user}: {question}")
        
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
        
    except Exception as e:
        logger.error(f"❌ Question error: {e}")
        await update.message.reply_text("Sorry, I encountered an error. Please try again.")

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