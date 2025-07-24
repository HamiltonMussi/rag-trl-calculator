"""Service for building LLM prompts with enhanced prompting techniques.

Balanced version maintaining technique organization with improved clarity and conciseness.
Techniques: Role Prompting, Chain-of-Thought, Meta Prompting, RAG.
"""

import logging
from typing import List, Dict, Tuple
from .validation import InputValidator, ValidationError

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Balanced prompt constructor for TRL analysis with organized prompting techniques."""
    
    # ========================================
    # ROLE PROMPTING TECHNIQUE
    # ========================================
    # Clear AI assistant role definition with core directives
    _ROLE_DEFINITION = (
        "Você é um assistente de IA especializado em Technology Readiness Level (TRL) para aplicações militares. "
        "Diretriz principal: PRECISÃO e FIDELIDADE aos fatos. NÃO INVENTE informações.\n"
        "Avalie maturidade tecnológica EXCLUSIVAMENTE baseado nos documentos fornecidos.\n"
    )
    
    # ========================================
    # CHAIN-OF-THOUGHT PROMPTING TECHNIQUE
    # ========================================
    # Systematic reasoning process for comprehensive analysis
    _CHAIN_OF_THOUGHT_INSTRUCTIONS = (
        "PROCESSO DE ANÁLISE SISTEMÁTICA:\n"
        "1. IDENTIFICAÇÃO: Identifique conceitos-chave e critérios TRL na pergunta\n"
        "2. ANÁLISE: Examine evidências disponíveis nos documentos fornecidos\n"
        "3. AVALIAÇÃO: Compare alternativas com critérios TRL estabelecidos\n"
        "4. ELIMINAÇÃO: Descarte alternativas sem suporte no contexto\n"
        "5. SELEÇÃO: Escolha alternativa mais precisa baseada em evidências\n"
        "6. JUSTIFICATIVA: Forneça reasoning claro citando fontes específicas\n\n"
    )
    
    # ========================================
    # CORE INSTRUCTIONS & RAG TECHNIQUE
    # ========================================
    # Essential response rules with source citation requirements
    _CORE_INSTRUCTIONS = (
        "RECURSOS DISPONÍVEIS:\n"
        "1. Glossário técnico (priorize sempre o contexto documental)\n"
        "2. Documentos específicos (fornecidos como 'Contexto' com origem: 'Fonte: Documento.pdf, Seção: X')\n\n"
        
        "REGRAS DE RESPOSTA:\n"
        "• IMPERATIVO: Respeite OBRIGATORIAMENTE estrutura de alternativas/questões fornecidas\n"
        "• IMPERATIVO: Siga EXATAMENTE o 'Formato de Resposta Requerido' quando fornecido na pergunta\n"
        "• IMPERATIVO: Use APENAS os rótulos/cabeçalhos especificados no formato (ex: '**Resposta:**', '**Justificativa:**')\n"
        "• IMPERATIVO: Mantenha a ORDEM EXATA dos elementos do formato requerido\n"
        "• Justificativa BREVE e DIRETA baseada estritamente no 'Contexto'\n"
        "• NÃO mencione alternativas não fornecidas, NÃO responda perguntas não feitas\n"
        "• CITE FONTES explicitamente: '(Fonte: Documento.pdf, Seção Y)'\n"
        "• Se não há informações suficientes: responda 'DESCONHECIDO' + motivo específico\n"
        "• Mantenha resposta CURTA e OBJETIVA em português\n\n"
    )
    
    # ========================================
    # META PROMPTING TECHNIQUE
    # ========================================
    # Self-verification checklist for quality control
    _META_PROMPTING_CHECKLIST = (
        "VERIFICAÇÃO FINAL - Confirme antes de responder:\n"
        "✓ Segui EXATAMENTE o 'Formato de Resposta Requerido'?\n"
        "✓ Usei APENAS os rótulos especificados (ex: **Resposta:**, **Justificativa:**)?\n"
        "✓ Mantive a ORDEM EXATA dos elementos?\n"
        "✓ Baseado exclusivamente no contexto?\n"
        "✓ Fontes citadas adequadamente?\n"
        "✓ Alternativa mais precisa?\n"
        "✓ Justificativa clara e factual?\n"
        "✓ Processo sistemático seguido?\n"
        "✓ 'DESCONHECIDO' se não há informações suficientes?\n"
    )
    
    # ========================================
    # COMPLETE SYSTEM PROMPT TEMPLATE
    # ========================================
    # Combines all prompting techniques into cohesive system prompt
    SYSTEM_PROMPT_TEMPLATE = (
        _ROLE_DEFINITION + "\n" +
        _CORE_INSTRUCTIONS +
        _CHAIN_OF_THOUGHT_INSTRUCTIONS +
        _META_PROMPTING_CHECKLIST
    )
    
    def __init__(self):
        self.validator = InputValidator()
    
    def build_prompt_and_messages(
        self, 
        technology_id: str, 
        context: str, 
        question: str
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Build system prompt and message list for LLM.
        
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
            # Validate inputs
            validated_tech_id = self.validator.validate_technology_id(technology_id)
            validated_context = self.validator.validate_context(context)
            validated_question = self.validator.validate_question(question)
            
            # Build user content
            user_content = self._build_user_content(
                validated_tech_id, 
                validated_context, 
                validated_question
            )
            
            # Create messages structure
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT_TEMPLATE},
                {"role": "user", "content": user_content},
            ]
            
            # Final validation
            validated_messages = self.validator.validate_messages(messages)
            
            logger.debug(f"Built prompt for technology: {validated_tech_id}")
            return self.SYSTEM_PROMPT_TEMPLATE, validated_messages
            
        except ValidationError as e:
            logger.error(f"Validation error in prompt building: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in prompt building: {e}", exc_info=True)
            raise ValidationError(f"Failed to build prompt: {str(e)}")
    
    def _build_user_content(self, technology_id: str, context: str, question: str) -> str:
        """
        Build the user content section.
        
        Chain-of-Thought instructions are included in the system prompt.
        """
        return f"### Tecnologia: {technology_id}\n### Contexto\n{context}\n\n### Pergunta\n{question}"
    
    
    def build_local_llm_prompt(self, system_content: str, user_content: str) -> str:
        """
        Build prompt for local LLM with instruction format.
        
        Args:
            system_content: System instructions
            user_content: User question and context
            
        Returns:
            Formatted prompt string
        """
        try:
            if not user_content.strip():
                raise ValidationError("User content cannot be empty")
            
            if system_content.strip():
                full_instruction = f"{system_content}\n\n{user_content}"
            else:
                logger.warning("System content is empty, using user content only")
                full_instruction = user_content
            
            return f"<instruction>{full_instruction.strip()}</instruction>"
            
        except Exception as e:
            logger.error(f"Error building local LLM prompt: {e}")
            raise ValidationError(f"Failed to build local LLM prompt: {str(e)}")
    
    def get_truncated_prompt_for_logging(self, prompt: str, max_length: int = 2000) -> str:
        """Get a truncated version of prompt for logging purposes."""
        if len(prompt) <= max_length:
            return prompt
        
        half_length = max_length // 2 - 20
        return f"{prompt[:half_length]}...[TRUNCATED]...{prompt[-half_length:]}"