#!/usr/bin/env python3
"""
Generic script to add any text file to the vector database.
Usage: python add_any_dataset.py <filename>
"""

import logging
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pathlib import Path
import sys
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GenericDatasetAdder:
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
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection("documents")
            logger.info(f"Connected to existing collection with {self.collection.count()} documents")
        except Exception:
            logger.info("Creating new collection...")
            self.collection = self.client.create_collection("documents")
            logger.info("New collection created")
        
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
    
    def add_documents(self, documents, file_name):
        """Add documents to the vector database."""
        try:
            # Check if file already exists in database
            existing_docs = self.collection.get(
                where={"file_name": Path(file_name).name}
            )
            
            if existing_docs['ids']:
                logger.warning(f"File '{Path(file_name).name}' already exists in database with {len(existing_docs['ids'])} documents")
                response = input("Do you want to replace it? (y/n): ").lower().strip()
                if response == 'y':
                    logger.info("Deleting existing documents...")
                    self.collection.delete(where={"file_name": Path(file_name).name})
                    logger.info("Existing documents deleted")
                else:
                    logger.info("Skipping addition. File already exists.")
                    return
            
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

    def list_files_in_database(self):
        """List all files currently in the database."""
        try:
            # Get all metadata
            all_data = self.collection.get()
            
            if not all_data['metadatas']:
                logger.info("No files found in database")
                return
            
            # Count documents per file
            file_counts = {}
            for metadata in all_data['metadatas']:
                file_name = metadata.get('file_name', 'Unknown')
                file_counts[file_name] = file_counts.get(file_name, 0) + 1
            
            logger.info("Files currently in database:")
            for file_name, count in file_counts.items():
                logger.info(f"  - {file_name}: {count} documents")
            
            logger.info(f"Total documents: {len(all_data['metadatas'])}")
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")

def main():
    """Main function to add dataset."""
    parser = argparse.ArgumentParser(description='Add any text file to the vector database')
    parser.add_argument('filename', nargs='?', help='Text file to add to the database')
    parser.add_argument('--list', action='store_true', help='List files currently in database')
    
    args = parser.parse_args()
    
    try:
        logger.info("🚀 Starting Generic Dataset Manager...")
        
        # Initialize the dataset adder
        adder = GenericDatasetAdder()
        
        # If --list flag is used, show current files
        if args.list:
            adder.list_files_in_database()
            return
        
        # Check if filename is provided
        if not args.filename:
            logger.error("Please provide a filename or use --list to see current files")
            logger.info("Usage: python add_any_dataset.py <filename>")
            logger.info("       python add_any_dataset.py --list")
            sys.exit(1)
        
        # Check if file exists
        if not Path(args.filename).exists():
            logger.error(f"File '{args.filename}' not found!")
            sys.exit(1)
        
        # Load and process the dataset
        documents = adder.load_and_process_text_file(args.filename)
        
        # Add to vector database
        adder.add_documents(documents, args.filename)
        
        logger.info("✅ Dataset addition completed successfully!")
        logger.info(f"File '{args.filename}' has been added to the database")
        
        # Show current database status
        logger.info("\nCurrent database status:")
        adder.list_files_in_database()
        
    except Exception as e:
        logger.error(f"❌ Error during dataset addition: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()