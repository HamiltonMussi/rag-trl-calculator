import re, uuid, pathlib, json
from docx import Document
from chromadb import PersistentClient
from hf_utils import get_hf_embeddings
from typing import List, Dict
import numpy as np

ROOT = pathlib.Path(__file__).parent
client = PersistentClient(str(ROOT / "store"))
collection = client.get_or_create_collection("trl")

def add_doc(text: str, meta: dict):
    emb = get_hf_embeddings([text])[0]
    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[text],
        embeddings=[emb],
        metadatas=[meta],
    )

def get_embedding(text: str) -> List[float]:
    """Get embedding for a text using Hugging Face Sentence Transformer"""
    return get_hf_embeddings([text])[0]

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def create_semantic_chunks(glossary_text: str, similarity_threshold: float = 0.7) -> List[Dict]:
    """Create semantic chunks from glossary text by grouping related terms"""
    # First, split into individual term-definition pairs
    raw_entries = []
    for block in re.split(r"\n{2,}", glossary_text):
        parts = block.strip().split("\n", 1)
        if len(parts) == 2:
            term, definition = parts
            raw_entries.append({
                "term": term.strip(),
                "definition": definition.strip(),
                "embedding": get_embedding(definition)
            })
    
    # Group related entries based on semantic similarity
    chunks = []
    current_chunk = []
    current_chunk_embedding = None
    
    for entry in raw_entries:
        if not current_chunk:
            # Start new chunk
            current_chunk.append(entry)
            current_chunk_embedding = entry["embedding"]
        else:
            # Calculate similarity with current chunk
            similarity = cosine_similarity(entry["embedding"], current_chunk_embedding)
            
            if similarity >= similarity_threshold and len(current_chunk) < 5:  # Limit chunk size
                # Add to current chunk
                current_chunk.append(entry)
                # Update chunk embedding (average of all embeddings)
                current_chunk_embedding = np.mean([e["embedding"] for e in current_chunk], axis=0)
            else:
                # Save current chunk and start new one
                chunks.append({
                    "text": "\n\n".join([f"{e['term']}\n{e['definition']}" for e in current_chunk]),
                    "terms": [e["term"] for e in current_chunk],
                    "type": "glossary_chunk"
                })
                current_chunk = [entry]
                current_chunk_embedding = entry["embedding"]
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append({
            "text": "\n\n".join([f"{e['term']}\n{e['definition']}" for e in current_chunk]),
            "terms": [e["term"] for e in current_chunk],
            "type": "glossary_chunk"
        })
    
    return chunks

# --- Word report ---------------------------------------------------------
# Temporarily disabled for RAG improvements
# doc = Document(ROOT / "data" / "Relatorio TRL Anotado V1.docx")
# buffer = []
# for para in doc.paragraphs:
#     txt = para.text.strip()
#     if txt.startswith("RELATÓRIO TRL"):
#         # flush previous section
#         if buffer:
#             add_doc("\n".join(buffer), {"type": "relatorio"})
#             buffer = []
#     if txt:
#         buffer.append(txt)
# # last chunk
# if buffer:
#     add_doc("\n".join(buffer), {"type": "relatorio"})

# --- Glossary ------------------------------------------------------------
print("Loading glossary...")
gloss = pathlib.Path(ROOT / "data" / "glossario.txt").read_text(encoding="utf-8")

print("Creating semantic chunks...")
chunks = create_semantic_chunks(gloss)

print(f"Created {len(chunks)} semantic chunks")
for chunk in chunks:
    add_doc(chunk["text"], {
        "type": "glossary_chunk",
        "terms": ", ".join(chunk["terms"]),  # Convert list to comma-separated string
        "chunk_size": len(chunk["terms"])
    })

print("Finished indexing")