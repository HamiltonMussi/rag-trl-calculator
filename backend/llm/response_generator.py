from transformers import pipeline, GenerationConfig, AutoTokenizer, AutoModelForCausalLM
from functools import lru_cache
import torch
import logging
from typing import List, Dict
import os
from config import USE_LOCAL_LLM, LOCAL_LLM_MODEL_ID, OPENAI_MODEL_NAME, OPENAI_API_KEY

try:
    import openai
except ImportError:
    openai = None

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

@lru_cache(maxsize=1)
def get_llm_components(model_id: str = "TucanoBR/Tucano-1b1-Instruct"):
    logger.info(f"Loading LLM model and tokenizer: {model_id} on device: {device}")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id)
    model.to(device)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    if model.config.pad_token_id is None:
        model.config.pad_token_id = tokenizer.pad_token_id
    generation_config = GenerationConfig(
        max_new_tokens=1024,
        do_sample=True,
        temperature=0.6,
        top_p=0.95,
        repetition_penalty=1.15,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    pipeline_device = str(device) if device.type == 'mps' else (device.index if device.type == 'cuda' else -1)
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        device=pipeline_device,
        generation_config=generation_config
    )
    logger.info(f"LLM pipeline for {model_id} created successfully on device: {pipeline_device}.")
    return pipe, tokenizer, model

def call_openai_llm(messages):
    if openai is None:
        raise ImportError("openai package is not installed. Please add it to your environment.")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in environment or .env file.")
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL_NAME,
        messages=messages,
        temperature=0.0,  # deterministic
        max_tokens=2048,  # increased max tokens
        top_p=1.0,
        n=1,
    )
    return response.choices[0].message.content.strip()

def generate_llm_response(messages: List[Dict], model_id: str = None) -> str:
    """
    If USE_LOCAL_LLM is True, use local model; otherwise, use OpenAI API.
    model_id is only used for local LLM.
    """
    if USE_LOCAL_LLM:
        text_generation_pipeline, _, _ = get_llm_components(model_id or LOCAL_LLM_MODEL_ID)
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
        log_prompt = prompt if len(prompt) < 2000 else prompt[:1000] + "...[TRUNCATED]..." + prompt[-1000:]
        logger.info(f"Generating LLM response. Full constructed prompt:\n{log_prompt}")
        try:
            generated_outputs = text_generation_pipeline(prompt, num_return_sequences=1)
            raw_response_text = generated_outputs[0]['generated_text']
            actual_response = raw_response_text
            if raw_response_text.startswith(prompt):
                actual_response = raw_response_text[len(prompt):].strip()
            else:
                instruction_end_tag = "</instruction>"
                idx = raw_response_text.find(instruction_end_tag)
                if idx != -1:
                    actual_response = raw_response_text[idx + len(instruction_end_tag):].strip()
                else:
                    logger.warning(
                        f"LLM response did not start with the prompt nor was '</instruction>' found cleanly. Prompt: {log_prompt[:200]}..., Response: {raw_response_text[:200]}... Returning raw response."
                    )
            logger.info(f"LLM raw response snippet: {raw_response_text[:300]}... Cleaned response snippet: {actual_response[:300]}...")
            return actual_response
        except Exception as e:
            logger.error(f"Error during LLM generation for prompt beginning with '{prompt[:200]}...': {e}", exc_info=True)
            return f"Erro crítico ao gerar resposta do LLM: {str(e)}"
    else:
        # Use OpenAI API
        try:
            logger.info("Calling OpenAI LLM API with provided messages.")
            return call_openai_llm(messages)
        except Exception as e:
            logger.error(f"Error during OpenAI LLM call: {e}", exc_info=True)
            return f"Erro crítico ao gerar resposta do LLM externo: {str(e)}" 