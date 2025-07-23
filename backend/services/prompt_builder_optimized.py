"""Optimized prompt builder with compressed prompts for smaller models."""

import logging
from typing import List, Dict, Tuple
from .validation import InputValidator, ValidationError

logger = logging.getLogger(__name__)


class OptimizedPromptBuilder:
    """Ultra-compressed prompt builder maintaining all original information."""
    
    # Compressed system prompt combining all techniques
    SYSTEM_PROMPT_TEMPLATE = (
        "Você é especialista TRL militar. NÃO INVENTE dados. Use APENAS documentos/contexto fornecidos.\n\n"
        
        "Processo obrigatório:\n"
        "1. Identifique critérios TRL relevantes\n"
        "2. Examine evidências no contexto\n" 
        "3. Compare alternativas com critérios\n"
        "4. Elimine alternativas inadequadas\n"
        "5. Selecione mais precisa\n"
        "6. Justifique citando fontes\n\n"
        
        "Regras:\n"
        "• SEMPRE cite fonte+seção (ex: RelatorioTec.pdf, Seção X)\n"
        "• Responda INCOMPLETO se dados insuficientes\n"
        "• Mantenha respostas objetivas\n"
        "• Use apenas alternativas fornecidas\n"
        "• Fundamente em contexto explícito\n\n"
        
        "Verificação final:\n"
        "✓ Baseado exclusivamente no contexto?\n"
        "✓ Fontes citadas corretamente?\n" 
        "✓ Alternativa mais precisa?\n"
        "✓ Justificativa clara/factual?\n"
        "✓ Processo sistemático seguido?\n"
        "✓ INCOMPLETO se evidências insuficientes?"
    )
    
    def __init__(self):
        self.validator = InputValidator()
    
    def build_prompt_and_messages(
        self, 
        technology_id: str, 
        context: str, 
        question: str
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Build optimized system prompt and message list."""
        try:
            # Validate inputs
            validated_tech_id = self.validator.validate_technology_id(technology_id)
            validated_context = self.validator.validate_context(context)
            validated_question = self.validator.validate_question(question)
            
            # Build compact user content
            user_content = f"Tecnologia: {validated_tech_id}\nContexto:\n{validated_context}\n\nPergunta: {validated_question}"
            
            # Create messages
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT_TEMPLATE},
                {"role": "user", "content": user_content},
            ]
            
            validated_messages = self.validator.validate_messages(messages)
            
            logger.debug(f"Built optimized prompt for: {validated_tech_id}")
            return self.SYSTEM_PROMPT_TEMPLATE, validated_messages
            
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error building prompt: {e}", exc_info=True)
            raise ValidationError(f"Failed to build prompt: {str(e)}")
    
    def build_local_llm_prompt(self, system_content: str, user_content: str) -> str:
        """Build prompt for local LLM."""
        try:
            if not user_content.strip():
                raise ValidationError("User content cannot be empty")
            
            full_instruction = f"{system_content}\n\n{user_content}" if system_content.strip() else user_content
            return f"<instruction>{full_instruction.strip()}</instruction>"
            
        except Exception as e:
            logger.error(f"Error building local LLM prompt: {e}")
            raise ValidationError(f"Failed to build local LLM prompt: {str(e)}")
    
    def get_truncated_prompt_for_logging(self, prompt: str, max_length: int = 2000) -> str:
        """Get truncated version for logging."""
        if len(prompt) <= max_length:
            return prompt
        
        half_length = max_length // 2 - 20
        return f"{prompt[:half_length]}...[TRUNCATED]...{prompt[-half_length:]}"