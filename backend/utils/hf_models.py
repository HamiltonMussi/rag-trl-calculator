from transformers import AutoTokenizer, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer
from functools import lru_cache
import torch
import logging
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_device():
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    else:
        return torch.device("cpu")

device = get_device()
logger.info(f"Using HF device: {device}")

@lru_cache(maxsize=1)
def get_embedding_model_instance(model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    logger.info(f"Loading sentence transformer model: {model_name} on device: {device}")
    model = SentenceTransformer(model_name, device=str(device))
    logger.info(f"Sentence transformer model {model_name} loaded successfully.")
    return model

def get_hf_embeddings(texts: List[str], model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") -> List[List[float]]:
    model = get_embedding_model_instance(model_name)
    if not texts:
        logger.info("get_hf_embeddings called with no texts.")
        return []
    logger.info(f"Generating embeddings for {len(texts)} texts. First text snippet: '{str(texts[0])[:100]}...'")
    valid_texts = [str(text) if text is not None else "" for text in texts]
    embeddings = model.encode(valid_texts, convert_to_tensor=False, show_progress_bar=False)
    logger.info("Embeddings generated.")
    return [emb.tolist() for emb in embeddings]

@lru_cache(maxsize=1)
def get_just_tokenizer(model_id: str):
    logger.info(f"Loading ONLY tokenizer for model: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    logger.info(f"Tokenizer for {model_id} loaded successfully.")
    return tokenizer 