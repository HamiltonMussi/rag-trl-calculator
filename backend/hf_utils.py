from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, GenerationConfig
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import torch
from functools import lru_cache
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine device
if torch.backends.mps.is_available() and torch.backends.mps.is_built():
    device = torch.device("mps")
elif torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")
logger.info(f"Using HF device: {device}")

# --- Embedding Model ---
@lru_cache(maxsize=1)
def get_embedding_model_instance(model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    logger.info(f"Loading sentence transformer model: {model_name} on device: {device}")
    # SentenceTransformer device parameter expects a string like 'cpu', 'cuda', 'cuda:0', 'mps'
    model = SentenceTransformer(model_name, device=str(device))
    logger.info(f"Sentence transformer model {model_name} loaded successfully.")
    return model

@lru_cache(maxsize=1)
def get_just_tokenizer(model_id: str = "TucanoBR/Tucano-2b4-Instruct"):
    """Loads and returns only the tokenizer for the specified model_id."""
    logger.info(f"Loading ONLY tokenizer for model: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    logger.info(f"Tokenizer for {model_id} loaded successfully.")
    return tokenizer

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

# --- LLM ---
@lru_cache(maxsize=1)
def get_llm_components(model_id: str = "TucanoBR/Tucano-2b4-Instruct"):
    logger.info(f"Loading LLM model and (again, if not cached) tokenizer: {model_id} on device: {device}")
    # Tokenizer might be loaded again here if get_just_tokenizer wasn't called first,
    # but AutoTokenizer.from_pretrained is often smart about local cache.
    tokenizer = AutoTokenizer.from_pretrained(model_id) 
    # For LLMs that are very large, consider low_cpu_mem_usage=True if RAM is an issue during initial load before .to(device)
    model = AutoModelForCausalLM.from_pretrained(model_id) 
    model.to(device)

    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    if model.config.pad_token_id is None:
         model.config.pad_token_id = tokenizer.pad_token_id # Use tokenizer's pad_token_id
    
    generation_config = GenerationConfig(
        max_new_tokens=1024,
        do_sample=True,
        temperature=0.6,
        top_p=0.95, # Adjusted top_p
        repetition_penalty=1.15, # Adjusted repetition_penalty
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    
    # device for pipeline: -1 for CPU, 0 for first GPU, 'mps' for Apple Silicon GPU.
    pipeline_device = str(device) if device.type == 'mps' else (device.index if device.type == 'cuda' else -1)

    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        device=pipeline_device,
        generation_config=generation_config
    )
    logger.info(f"LLM pipeline for {model_id} created successfully on device: {pipeline_device}.")
    return pipe, tokenizer, model # Return model for direct use if needed elsewhere

def generate_llm_response(messages: List[Dict], model_id: str = "TucanoBR/Tucano-2b4-Instruct") -> str:
    text_generation_pipeline, _, _ = get_llm_components(model_id)
    
    system_content = ""
    user_content = ""

    for msg in messages:
        if msg['role'] == 'system':
            system_content = msg['content']
        elif msg['role'] == 'user':
            user_content = msg['content']

    if not user_content:
        logger.error("User content is empty for LLM. Cannot generate response.")
        return "Erro: Conteúdo do usuário fornecido para o LLM está vazio."
    if not system_content:
        logger.warning("System content is empty for LLM. Proceeding with user content only for instruction.")

    full_instruction = f"{system_content}\n\n{user_content}" if system_content else user_content
    prompt = f"<instruction>{full_instruction.strip()}</instruction>"
    
    # Log the full prompt if it's not excessively long, otherwise a significant portion
    log_prompt = prompt if len(prompt) < 2000 else prompt[:1000] + "...[TRUNCATED]..." + prompt[-1000:]
    logger.info(f"Generating LLM response. Full constructed prompt:\n{log_prompt}")
    
    try:
        generated_outputs = text_generation_pipeline(prompt, num_return_sequences=1)
        raw_response_text = generated_outputs[0]['generated_text']
        
        # Strategy to remove the prompt from the response:
        # 1. Check if the response starts with the exact prompt.
        # 2. If not, check if it starts with "<instruction>" and try to find the closing "</instruction>".
        actual_response = raw_response_text
        
        if raw_response_text.startswith(prompt):
            actual_response = raw_response_text[len(prompt):].strip()
        else:
            # Fallback: try to find the end of the instruction block if model didn't echo perfectly
            instruction_end_tag = "</instruction>"
            # Find the *last* occurrence of the end tag, in case it appears in the prompt itself.
            # However, the model is more likely to place its answer *after* the main instruction block.
            idx = raw_response_text.find(instruction_end_tag) # Find first, assuming it's the end of the prompt echo
            if idx != -1:
                actual_response = raw_response_text[idx + len(instruction_end_tag):].strip()
            else:
                logger.warning(
                    f"LLM response did not start with the prompt nor was '</instruction>' found cleanly. Prompt: {log_prompt[:200]}..., Response: {raw_response_text[:200]}... Returning raw response."
                )
                # Keep actual_response as raw_response_text if no clear way to strip

        logger.info(f"LLM raw response snippet: {raw_response_text[:300]}... Cleaned response snippet: {actual_response[:300]}...")
        return actual_response

    except Exception as e:
        logger.error(f"Error during LLM generation for prompt beginning with '{prompt[:200]}...': {e}", exc_info=True)
        return f"Erro crítico ao gerar resposta do LLM: {str(e)}"

def get_llm_tokenizer(model_id: str = "TucanoBR/Tucano-2b4-Instruct"):
    """This function is intended to get the tokenizer associated with the full LLM pipeline."""
    # It still relies on get_llm_components, which loads the full model.
    # For tokenizer-only needs (like chunking), use get_just_tokenizer.
    _, tokenizer, _ = get_llm_components(model_id)
    return tokenizer 