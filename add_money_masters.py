#!/usr/bin/env python3
"""
Script to add The Money Masters dataset to existing vector database.
"""

import logging
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatasetAdder:
    def __init__(self):
        self.db_path = Path("./chroma_db")
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get existing collection
        try:
            self.collection = self.client.get_collection("documents")
            logger.info(f"Connected to existing collection with {self.collection.count()} documents")
        except Exception:
            logger.error("No existing collection found. Please run the original initialization first.")
            sys.exit(1)
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def load_and_process_text_file(self, file_path: str):
        """Load and chunk text file into documents."""
        try:
            logger.info(f"Loading file: {file_path}")
            
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        content = file.read()
                    logger.info(f"Successfully loaded file with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise Exception("Could not decode file with any common encoding")
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(content)
            logger.info(f"Created {len(chunks)} chunks from {file_path}")
            
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
            
            return documents
        
        except Exception as e:
            logger.error(f"Error loading text file {file_path}: {e}")
            raise
    
    def add_documents(self, documents):
        """Add documents to the existing vector database."""
        try:
            # Get current count for ID generation
            current_count = self.collection.count()
            logger.info(f"Current database has {current_count} documents")
            
            # Extract text content and metadata
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            
            # Generate embeddings
            logger.info("Generating embeddings for new documents...")
            embeddings = self.embedding_model.encode(texts).tolist()
            
            # Generate unique IDs starting from current count
            ids = [f"doc_{current_count + i}" for i in range(len(documents))]
            
            # Add to collection
            logger.info("Adding documents to vector database...")
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            new_count = self.collection.count()
            logger.info(f"Successfully added {len(documents)} documents!")
            logger.info(f"Database now has {new_count} total documents")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}")
            raise

def main():
    """Main function to add The Money Masters dataset."""
    import glob
    
    # Find The Money Masters file using pattern matching
    money_masters_files = glob.glob("*Money Masters*.txt")
    
    if not money_masters_files:
        logger.error(f"No Money Masters text file found!")
        logger.info("Please make sure 'The Money Masters' text file is in the current directory.")
        sys.exit(1)
    
    dataset_file = money_masters_files[0]
    logger.info(f"Found file: {dataset_file}")
    
    try:
        logger.info("🚀 Starting The Money Masters dataset addition...")
        
        # Initialize the dataset adder
        adder = DatasetAdder()
        
        # Load and process the new dataset
        documents = adder.load_and_process_text_file(dataset_file)
        
        # Add to existing vector database
        adder.add_documents(documents)
        
        logger.info("✅ The Money Masters dataset addition completed successfully!")
        logger.info("Your bot can now answer questions from all three datasets:")
        logger.info("  - EBUPT200709.txt (Quantitative Finance)")
        logger.info("  - TheIntelligentInvestor.txt")
        logger.info("  - The Money Masters")
        
    except Exception as e:
        logger.error(f"❌ Error during dataset addition: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()