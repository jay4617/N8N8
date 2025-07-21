#!/usr/bin/env python3
"""
Simple working bot without complex async issues.
"""

import logging
import sys
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import Config

# Setup logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Global services
qa_service = None

def init_services():
    """Initialize AI services."""
    global qa_service
    
    try:
        logger.info("Loading AI services...")
        
        from vector_db import VectorDatabase
        from llm_service import DeepSeekService, QuestionAnsweringService
        
        vector_db = VectorDatabase()
        llm_service = DeepSeekService()
        qa_service = QuestionAnsweringService(vector_db, llm_service)
        
        logger.info("✅ AI services ready!")
        return True
    except Exception as e:
        logger.error(f"❌ Service load failed: {e}")
        return False

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

Commands:
/help - How to use me
/about - Learn about my capabilities

Ask me any quantitative finance question to get started!"""
        
        await update.message.reply_text(response)
        logger.info(f"✅ Sent /start response to {user}")
        
    except Exception as e:
        logger.error(f"❌ Start command error: {e}")
        await update.message.reply_text("Error in /start command")

async def help_handler(update, context):
    """Handle /help command."""
    try:
        response = """💡 How to use me:

I'm powered by advanced AI and have deep knowledge of quantitative finance. Simply ask me questions in natural language about:

📈 **Portfolio Management**
• Portfolio optimization techniques
• Asset allocation strategies
• Risk-return analysis

📊 **Risk Management** 
• Value at Risk (VaR) calculations
• Credit risk modeling
• Market risk assessment

💱 **Derivatives & Instruments**
• Options pricing models
• Futures and forwards
• Swaps and structured products

🔢 **Mathematical Finance**
• Stochastic calculus
• Monte Carlo methods
• Statistical models

Just type your question and I'll provide detailed, accurate answers!"""
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"❌ Help command error: {e}")

async def about_handler(update, context):
    """Handle /about command."""
    try:
        response = """ℹ️ About This Bot

🤖 **AI Technology**
Powered by state-of-the-art Large Language Models and advanced Retrieval-Augmented Generation (RAG) technology.

📚 **Knowledge Base**
Trained on comprehensive quantitative finance literature including:
• Academic papers and textbooks
• Industry best practices
• Mathematical models and formulas
• Real-world case studies

🎯 **Capabilities**
• Answer complex quantitative finance questions
• Explain mathematical concepts clearly
• Provide practical insights and examples
• Support both theoretical and applied finance

🔒 **Privacy**
Your conversations are processed securely. No personal financial data is stored.

Built with ❤️ for finance professionals and students."""
        
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"❌ About command error: {e}")

async def question_handler(update, context):
    """Handle questions."""
    try:
        if not qa_service:
            await update.message.reply_text("⏳ AI loading... try /test first")
            return
        
        user = update.effective_user.first_name or "User"
        question = update.message.text
        
        logger.info(f"📝 Question from {user}: {question}")
        
        # Show typing
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Get RAG answer
        result = await qa_service.answer_question(question)
        
        answer = result.get("answer", "No response generated")
        similarity = result.get("similarity_score", 0)
        has_context = result.get("has_context", False)
        context_len = result.get("context_length", 0)
        
        # Send clean response for production
        await update.message.reply_text(answer)
        logger.info(f"✅ Answered {user}")
        
    except Exception as e:
        logger.error(f"❌ Question error: {e}")
        await update.message.reply_text("😅 Something went wrong!")

def create_app():
    """Create the application."""
    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("about", about_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, question_handler))
    
    return app

if __name__ == "__main__":
    try:
        logger.info("🚀 Starting Simple Working Bot...")
        
        # Initialize services
        if not init_services():
            sys.exit(1)
        
        # Create and run app
        app = create_app()
        
        logger.info("✅ Bot ready! Starting polling...")
        app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)