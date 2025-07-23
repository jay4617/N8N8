import logging
import aiohttp
import json
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class DeepSeekService:
    def __init__(self):
        self.config = Config
        self.api_key = self.config.DEEPSEEK_API_KEY
        self.base_url = self.config.DEEPSEEK_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
<<<<<<< HEAD
    async def generate_response(self, query: str, context: str = "", max_tokens: int = 1000) -> Optional[str]:
=======
    async def generate_response(self, query: str, context: str = "", max_tokens: int = None) -> Optional[str]:
>>>>>>> 1e6e3ce (Update)
        """Generate response using DeepSeek API."""
        try:
            prompt = self._build_prompt(query, context)
            
<<<<<<< HEAD
            payload = {
                "model": "moonshotai/kimi-k2",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
=======
            # Use config values with fallback
            if max_tokens is None:
                max_tokens = self.config.MAX_TOKENS
            
            payload = {
                "model": self.config.MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "You are an expert in quantitative finance and trading."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": min(max_tokens, self.config.MAX_TOKENS),
                "temperature": self.config.TEMPERATURE,
                "top_p": self.config.TOP_P,
>>>>>>> 1e6e3ce (Update)
                "stream": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if "choices" in result and len(result["choices"]) > 0:
                            answer = result["choices"][0]["message"]["content"].strip()
                            logger.info(f"Generated response of {len(answer)} characters")
                            return answer
                        else:
                            logger.error("No choices in API response")
                            return None
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"MoonshotAI API error {response.status}: {error_text}")
                        return None
        
        except aiohttp.ClientTimeout:
            logger.error("MoonshotAI API request timed out")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error calling MoonshotAI API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling MoonshotAI API: {e}")
            return None
    
    def _build_prompt(self, query: str, context: str = "") -> str:
        """Build the prompt for the LLM."""
        if context:
            prompt = f"""You are an expert in quantitative finance. Answer the user's question based on the provided context from financial literature.

Context from Quantitative Finance knowledge base:
{context}

Question: {query}

Instructions:
- Use the provided context to answer the question comprehensively
- If the context is partially relevant, use what you can and explain the financial concepts clearly
- Provide detailed explanations for quantitative finance topics
- If you need more specific information not in the context, mention that
- Be educational and helpful

Answer:"""
        else:
            prompt = f"""You are an expert in quantitative finance. The user asked: {query}

Please provide a helpful response about this topic based on general quantitative finance knowledge.

Answer:"""
        
        return prompt
    
    async def test_connection(self) -> bool:
        """Test the connection to MoonshotAI API."""
        try:
            test_response = await self.generate_response("Hello", max_tokens=10)
            return test_response is not None
        except Exception as e:
            logger.error(f"MoonshotAI API connection test failed: {e}")
            return False

class QuestionAnsweringService:
    def __init__(self, vector_db, llm_service: DeepSeekService):
        self.vector_db = vector_db
        self.llm_service = llm_service
        self.config = Config
    
    async def answer_question(self, query: str) -> Dict[str, Any]:
        """Answer a question using RAG (Retrieval-Augmented Generation)."""
        try:
            # ALWAYS search the vector database for relevant content
            search_results = self.vector_db.similarity_search(query, n_results=5)
            
            if not search_results['documents']:
                return {
                    "answer": "Sorry, no content found in the knowledge base.",
                    "has_context": False,
                    "similarity_score": 0.0,
                    "context_used": False
                }
            
            # Get the best similarity score
            best_similarity = max(search_results['similarities']) if search_results['similarities'] else 0.0
            
            # Always use the best available context, regardless of similarity threshold
            # Combine top results for richer context
            context_parts = []
            for doc, similarity in zip(search_results['documents'][:3], search_results['similarities'][:3]):
                if doc and len(doc.strip()) > 0:
                    context_parts.append(doc.strip())
            
            if not context_parts:
                return {
                    "answer": "Sorry, no meaningful content found in the knowledge base.",
                    "has_context": False,
                    "similarity_score": best_similarity,
                    "context_used": False
                }
            
            # Combine context (limit to reasonable length)
            combined_context = "\n\n".join(context_parts)
            if len(combined_context) > 4000:  # Limit context length
                combined_context = combined_context[:4000] + "..."
            
            # ALWAYS generate response using the best available context
            response = await self.llm_service.generate_response(query, combined_context)
            
            return {
                "answer": response or "Sorry, I couldn't generate a response.",
                "has_context": True,
                "similarity_score": best_similarity,
                "context_used": True,
                "context_length": len(combined_context)
            }
        
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "answer": "Sorry, I encountered an error while processing your question.",
                "has_context": False,
                "similarity_score": 0.0,
                "context_used": False,
                "error": str(e)
            }