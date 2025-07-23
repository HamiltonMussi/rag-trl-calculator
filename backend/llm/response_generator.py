"""LLM response generation service with improved architecture."""

import logging
from typing import List, Dict, Tuple

from services.llm_client import LLMClientFactory
from services.prompt_builder_optimized import OptimizedPromptBuilder as PromptBuilder
from services.validation import ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Legacy functions for backward compatibility
def get_llm_components(model_id: str = "TucanoBR/Tucano-1b1-Instruct"):
    """
    DEPRECATED: Legacy function for getting LLM components.
    Use LLMClientFactory.create_client() instead.
    """
    logger.warning("Using deprecated get_llm_components function. Consider using LLMClientFactory.")
    from services.llm_client import LocalLLMClient
    client = LocalLLMClient(model_id)
    # Return pipeline for compatibility
    return client.pipeline, client._tokenizer, client._model

def call_openai_llm(messages: List[Dict[str, str]]) -> str:
    """
    Legacy function for OpenAI LLM calls.
    
    DEPRECATED: Use LLMClientFactory.create_client() instead.
    """
    logger.warning("Using deprecated call_openai_llm function. Consider using LLMClientFactory.")
    client = LLMClientFactory.create_client(use_local=False)
    return client.generate_response(messages)

def build_llm_prompt_and_messages(
    technology_id: str, 
    context: str, 
    question: str
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Build LLM prompt and messages for TRL analysis.
    
    Args:
        technology_id: Technology identifier
        context: Retrieved context for the question
        question: User's question
        
    Returns:
        Tuple of (system_prompt, messages_list)
        
    Raises:
        ValidationError: If inputs are invalid
    """
    try:
        prompt_builder = PromptBuilder()
        return prompt_builder.build_prompt_and_messages(technology_id, context, question)
    except ValidationError as e:
        logger.error(f"Validation error in prompt building: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in prompt building: {e}", exc_info=True)
        raise ValidationError(f"Failed to build prompt: {str(e)}")

def generate_llm_response(
    messages: List[Dict[str, str]], 
    model_id: str = None
) -> str:
    """
    Generate LLM response using configured client.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model_id: Optional model ID override for local LLM
        
    Returns:
        Generated response text
        
    Raises:
        ValidationError: If inputs are invalid
        Exception: If generation fails
    """
    try:
        # Create appropriate client
        client = LLMClientFactory.create_client(model_id=model_id)
        
        # Generate response
        logger.info("Generating LLM response")
        response = client.generate_response(messages)
        
        if not response.strip():
            raise ValueError("Empty response generated")
        
        logger.info(f"Generated response length: {len(response)} characters")
        return response
        
    except ValidationError as e:
        logger.error(f"Validation error in LLM generation: {e}")
        return f"Erro de validação: {str(e)}"
    except Exception as e:
        logger.error(f"Error during LLM generation: {e}", exc_info=True)
        return f"Erro crítico ao gerar resposta do LLM: {str(e)}" 