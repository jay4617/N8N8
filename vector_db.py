import logging
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from sentence_transformers import SentenceTransformer
import numpy as np
from config import Config

logger = logging.getLogger(__name__)

class VectorDatabase:
    def __init__(self):
        self.config = Config
        self.db_path = Path(self.config.CHROMA_DB_PATH)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection("documents")
            logger.info("Loaded existing document collection")
        except ValueError:
            self.collection = self.client.create_collection("documents")
            logger.info("Created new document collection")
        except Exception as e:
            logger.info(f"Collection not found, creating new: {e}")
            self.collection = self.client.create_collection("documents")
            logger.info("Created new document collection")
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.CHUNK_SIZE,
            chunk_overlap=self.config.CHUNK_OVERLAP,
            length_function=len,
        )
    
    def load_and_process_text_file(self, file_path: str) -> List[Document]:
        """Load and chunk text file into documents."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(content)
            
            # Create Document objects
            documents = []
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "source": file_path,
                        "chunk_id": i,
                        "file_name": Path(file_path).name
                    }
                )
                documents.append(doc)
            
            logger.info(f"Created {len(documents)} chunks from {file_path}")
            return documents
        
        except Exception as e:
            logger.error(f"Error loading text file {file_path}: {e}")
            raise
    
    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector database."""
        try:
            # Extract text content and metadata
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            
            # Generate embeddings
            logger.info("Generating embeddings for documents...")
            embeddings = self.embedding_model.encode(texts).tolist()
            
            # Generate IDs
            ids = [f"doc_{i}" for i in range(len(documents))]
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to vector database")
        
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}")
            raise
    
    def similarity_search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Perform similarity search on the vector database."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Calculate similarity scores (Chroma returns distances)
            similarities = []
            if results['distances'] and results['distances'][0]:
                # Convert distances to similarities (assuming cosine distance)
                similarities = [1 - distance for distance in results['distances'][0]]
            
            return {
                'documents': results['documents'][0] if results['documents'] else [],
                'metadatas': results['metadatas'][0] if results['metadatas'] else [],
                'similarities': similarities
            }
        
        except Exception as e:
            logger.error(f"Error performing similarity search: {e}")
            return {'documents': [], 'metadatas': [], 'similarities': []}
    
    def get_relevant_context(self, query: str, max_context_length: int = 3000) -> tuple[str, float]:
        """Get relevant context for a query with similarity check."""
        search_results = self.similarity_search(query, n_results=5)
        
        if not search_results['documents']:
            return "", 0.0
        
        # Check if best match meets similarity threshold
        best_similarity = max(search_results['similarities']) if search_results['similarities'] else 0.0
        
        if best_similarity < self.config.SIMILARITY_THRESHOLD:
            logger.info(f"Query similarity {best_similarity:.3f} below threshold {self.config.SIMILARITY_THRESHOLD}")
            return "", best_similarity
        
        # Combine relevant documents
        context_parts = []
        current_length = 0
        
        for doc, similarity in zip(search_results['documents'], search_results['similarities']):
            if similarity >= self.config.SIMILARITY_THRESHOLD:
                if current_length + len(doc) <= max_context_length:
                    context_parts.append(doc)
                    current_length += len(doc)
                else:
                    break
        
        context = "\n\n".join(context_parts)
        logger.info(f"Retrieved context of {len(context)} characters with max similarity {best_similarity:.3f}")
        
        return context, best_similarity
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database collection."""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": "documents",
                "embedding_model": "all-MiniLM-L6-v2"
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"total_documents": 0, "collection_name": "documents", "embedding_model": "all-MiniLM-L6-v2"}
    
    def get_available_topics(self, sample_size: int = 10) -> List[str]:
        """Get sample topics/subjects from the database."""
        try:
            # Get a sample of documents
            results = self.collection.get(limit=sample_size, include=['documents'])
            
            if not results['documents']:
                return []
            
            # Extract first sentence or first 100 characters from each document as topics
            topics = []
            for doc in results['documents']:
                # Get first sentence or first 100 chars
                first_sentence = doc.split('.')[0].strip()
                if len(first_sentence) > 100:
                    first_sentence = first_sentence[:100] + "..."
                if first_sentence and first_sentence not in topics:
                    topics.append(first_sentence)
            
            return topics[:5]  # Return top 5 unique topics
        
        except Exception as e:
            logger.error(f"Error getting available topics: {e}")
            return []
    
    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection("documents")
            self.collection = self.client.create_collection("documents")
            logger.info("Cleared all documents from vector database")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            raise