from transformers import AutoModelForCausalLM, AutoTokenizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_ID = "TucanoBR/Tucano-2b4-Instruct"
EMBEDDING_MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" # Also good to pre-download

def download_hf_model(model_id):
    logger.info(f"Attempting to download model: {model_id}...")
    try:
        # Download tokenizer
        logger.info(f"Downloading tokenizer for {model_id}...")
        AutoTokenizer.from_pretrained(model_id)
        logger.info(f"Tokenizer for {model_id} downloaded/cached.")

        # Download model
        logger.info(f"Downloading model weights for {model_id} (this may take a while)...")
        AutoModelForCausalLM.from_pretrained(model_id)
        logger.info(f"Model weights for {model_id} downloaded/cached successfully.")
    except Exception as e:
        logger.error(f"Error downloading model {model_id}: {e}", exc_info=True)

def download_sbert_model(model_id):
    from sentence_transformers import SentenceTransformer
    logger.info(f"Attempting to download sentence transformer model: {model_id}...")
    try:
        SentenceTransformer(model_id)
        logger.info(f"Sentence transformer model {model_id} downloaded/cached successfully.")
    except Exception as e:
        logger.error(f"Error downloading sentence transformer model {model_id}: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("--- Starting Hugging Face Model Download Script ---")

    logger.info(f"--- Downloading LLM: {MODEL_ID} ---")
    download_hf_model(MODEL_ID)

    logger.info(f"--- Downloading Embedding Model: {EMBEDDING_MODEL_ID} ---")
    download_sbert_model(EMBEDDING_MODEL_ID)
    
    logger.info("--- Model download script finished. ---")
    logger.info("Models should now be in your Hugging Face cache.")
    logger.info("Default cache directory is usually ~/.cache/huggingface/hub or similar.")
