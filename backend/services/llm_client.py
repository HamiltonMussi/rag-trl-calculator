"""LLM client abstraction layer for both local and external models."""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
from functools import lru_cache
from transformers import pipeline, GenerationConfig, AutoTokenizer, AutoModelForCausalLM
import torch

from config import USE_LOCAL_LLM, LOCAL_LLM_MODEL_ID, OPENAI_MODEL_NAME, OPENAI_API_KEY
from .device_manager import device_manager
from .validation import InputValidator, ValidationError
from .prompt_builder import PromptBuilder

try:
    import openai
except ImportError:
    openai = None

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate response from messages."""
        pass


class OpenAIClient(LLMClient):
    """Client for OpenAI API."""
    
    def __init__(self, api_key: str, model_name: str):
        self.validator = InputValidator()
        
        if not api_key:
            raise ValidationError("OpenAI API key is required")
        
        if openai is None:
            raise ImportError("openai package is not installed")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.model_name = model_name
        logger.info(f"Initialized OpenAI client with model: {model_name}")
    
    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate response using OpenAI API."""
        try:
            validated_messages = self.validator.validate_messages(messages)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=validated_messages,
                temperature=0.0,
                max_tokens=2048,
                top_p=1.0,
                n=1,
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI API")
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            raise


class LocalLLMClient(LLMClient):
    """Client for local Hugging Face models."""
    
    def __init__(self, model_id: str):
        self.validator = InputValidator()
        self.prompt_builder = PromptBuilder()
        self.model_id = self.validator.validate_model_id(model_id)
        self._pipeline = None
        self._tokenizer = None
        self._model = None
        logger.info(f"Initialized local LLM client with model: {model_id}")
    
    @property
    def pipeline(self):
        """Lazy load the LLM pipeline."""
        if self._pipeline is None:
            self._pipeline, self._tokenizer, self._model = self._load_model_components()
        return self._pipeline
    
    @lru_cache(maxsize=1)
    def _load_model_components(self):
        """Load and cache model components."""
        try:
            logger.info(f"Loading model components for: {self.model_id}")
            
            tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            model = AutoModelForCausalLM.from_pretrained(self.model_id)
            
            # Move model to optimal device
            device_manager.move_model_to_device(model)
            
            # Configure tokenizer
            self._configure_tokenizer(tokenizer, model)
            
            # Create generation config
            generation_config = self._create_generation_config(tokenizer)
            
            # Create pipeline
            pipeline_device = device_manager.get_pipeline_device_param()
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device=pipeline_device,
                generation_config=generation_config
            )
            
            logger.info(f"Model {self.model_id} loaded successfully on device: {device_manager.device}")
            return pipe, tokenizer, model
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_id}: {e}", exc_info=True)
            raise
    
    def _configure_tokenizer(self, tokenizer, model):
        """Configure tokenizer padding tokens."""
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token_id = tokenizer.eos_token_id
        if model.config.pad_token_id is None:
            model.config.pad_token_id = tokenizer.pad_token_id
    
    def _create_generation_config(self, tokenizer) -> GenerationConfig:
        """Create generation configuration."""
        return GenerationConfig(
            max_new_tokens=1024,
            do_sample=True,
            temperature=0.6,
            top_p=0.95,
            repetition_penalty=1.15,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    
    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate response using local model."""
        try:
            validated_messages = self.validator.validate_messages(messages)
            
            # Extract system and user content
            system_content, user_content = self._extract_message_content(validated_messages)
            
            # Build prompt for local model
            prompt = self.prompt_builder.build_local_llm_prompt(system_content, user_content)
            
            # Log truncated prompt
            log_prompt = self.prompt_builder.get_truncated_prompt_for_logging(prompt)
            logger.info(f"Generating response with prompt: {log_prompt}")
            
            # Generate response
            generated_outputs = self.pipeline(prompt, num_return_sequences=1)
            raw_response = generated_outputs[0]['generated_text']
            
            # Clean response
            cleaned_response = self._clean_response(raw_response, prompt)
            
            logger.info(f"Generated response length: {len(cleaned_response)} chars")
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Local LLM generation error: {e}", exc_info=True)
            raise
    
    def _extract_message_content(self, messages: List[Dict[str, str]]) -> Tuple[str, str]:
        """Extract system and user content from messages."""
        system_content = ""
        user_content = ""
        
        for msg in messages:
            if msg['role'] == 'system':
                system_content = msg['content']
            elif msg['role'] == 'user':
                user_content = msg['content']
        
        if not user_content:
            raise ValidationError("User content is required for local LLM")
        
        return system_content, user_content
    
    def _clean_response(self, raw_response: str, prompt: str) -> str:
        """Clean the generated response by removing prompt and instruction tags."""
        if raw_response.startswith(prompt):
            cleaned = raw_response[len(prompt):].strip()
        else:
            instruction_end_tag = "</instruction>"
            idx = raw_response.find(instruction_end_tag)
            if idx != -1:
                cleaned = raw_response[idx + len(instruction_end_tag):].strip()
            else:
                logger.warning("Could not find instruction end tag in response")
                cleaned = raw_response
        
        return cleaned


class LLMClientFactory:
    """Factory for creating appropriate LLM clients."""
    
    @staticmethod
    def create_client(use_local: bool = None, model_id: str = None) -> LLMClient:
        """
        Create appropriate LLM client based on configuration.
        
        Args:
            use_local: Override for USE_LOCAL_LLM config
            model_id: Override for model ID
            
        Returns:
            Configured LLM client
        """
        use_local_llm = use_local if use_local is not None else USE_LOCAL_LLM
        
        if use_local_llm:
            model_to_use = model_id or LOCAL_LLM_MODEL_ID
            return LocalLLMClient(model_to_use)
        else:
            return OpenAIClient(OPENAI_API_KEY, OPENAI_MODEL_NAME)