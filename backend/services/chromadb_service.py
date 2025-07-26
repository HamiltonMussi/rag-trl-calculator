"""ChromaDB service for document storage and retrieval."""

import pathlib
import logging
from typing import List, Dict, Optional, Tuple
from chromadb import PersistentClient

logger = logging.getLogger(__name__)


class ChromaDBService:
    """Service for managing ChromaDB operations."""
    
    def __init__(self, store_path: Optional[str] = None):
        """Initialize ChromaDB client."""
        if store_path is None:
            root = pathlib.Path(__file__).parent.parent
            store_path = str(root / "store")
        
        self.client = PersistentClient(store_path)
        logger.info(f"ChromaDB client initialized with store path: {store_path}")
    
    def get_technology_collection(self, tech_id: str):
        """Get or create a technology-specific collection."""
        collection_name = f"tech_{tech_id}"
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def get_trl_collection(self):
        """Get or create the TRL glossary collection."""
        return self.client.get_or_create_collection("trl")
    
    def add_document_chunks(
        self, 
        tech_id: str, 
        texts: List[str], 
        embeddings: List[List[float]], 
        metadatas: List[Dict], 
        chunk_ids: List[str]
    ) -> bool:
        """
        Add document chunks to a technology collection.
        
        Args:
            tech_id: Technology identifier
            texts: List of chunk texts
            embeddings: List of chunk embeddings
            metadatas: List of chunk metadata
            chunk_ids: List of unique chunk IDs
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if len(texts) != len(embeddings) != len(metadatas) != len(chunk_ids):
                raise ValueError("All input lists must have the same length")
            
            collection = self.get_technology_collection(tech_id)
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=chunk_ids
            )
            
            logger.info(f"Successfully added {len(texts)} chunks to collection 'tech_{tech_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Error adding chunks to collection 'tech_{tech_id}': {e}", exc_info=True)
            return False
    
    def remove_document_chunks(self, tech_id: str, filename: str) -> bool:
        """
        Remove all chunks for a specific document from a technology collection.
        
        Args:
            tech_id: Technology identifier
            filename: Name of the file to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self.get_technology_collection(tech_id)
            
            # Get all documents to find ones related to this file
            results = collection.get()
            
            # Find IDs of chunks that belong to this file
            ids_to_remove = []
            if results['metadatas']:
                for i, metadata in enumerate(results['metadatas']):
                    if metadata and metadata.get('source') == filename:
                        ids_to_remove.append(results['ids'][i])
            
            if ids_to_remove:
                collection.delete(ids=ids_to_remove)
                logger.info(f"Removed {len(ids_to_remove)} chunks for file '{filename}' from tech_{tech_id}")
            else:
                logger.info(f"No chunks found for file '{filename}' in tech_{tech_id}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error removing document '{filename}' from tech_{tech_id}: {e}", exc_info=True)
            return False
    
    def query_collection(
        self, 
        collection_name: str, 
        query_embedding: List[float], 
        n_results: int = 10
    ) -> Dict:
        """
        Query a collection with an embedding.
        
        Args:
            collection_name: Name of the collection to query
            query_embedding: Query embedding vector
            n_results: Number of results to return
            
        Returns:
            Query results from ChromaDB
        """
        try:
            if collection_name == "trl":
                collection = self.get_trl_collection()
            else:
                # Assume it's a technology collection
                tech_id = collection_name.replace("tech_", "")
                collection = self.get_technology_collection(tech_id)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.debug(f"Queried collection '{collection_name}' and got {len(results.get('documents', [[]])[0])} results")
            return results
            
        except Exception as e:
            logger.error(f"Error querying collection '{collection_name}': {e}", exc_info=True)
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists."""
        try:
            collections = self.client.list_collections()
            return collection_name in [col.name for col in collections]
        except Exception as e:
            logger.error(f"Error checking if collection '{collection_name}' exists: {e}")
            return False