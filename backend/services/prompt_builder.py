"""Service for building LLM prompts with consistent structure."""

import logging
from typing import List, Dict, Tuple
from .validation import InputValidator, ValidationError

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Handles prompt construction for TRL analysis."""
    
    SYSTEM_PROMPT_TEMPLATE = (
        "Você é um assistente de IA especializado em Tecnologia de Readiness Level (TRL) para aplicações militares. "
        "Sua principal diretriz é a precisão e a fidelidade aos fatos. NÃO INVENTE informações sob nenhuma circunstância.\n"
        "Sua função é ajudar a avaliar o nível de maturidade tecnológica de diferentes tecnologias "
        "com base EXCLUSIVAMENTE nos documentos e glossário fornecidos.\n"
        "Você tem acesso a:\n"
        "1. Um glossário de termos técnicos (implícito no seu conhecimento, mas priorize o contexto documental).\n"
        "2. Documentos específicos da tecnologia em análise (fornecidos como 'Contexto'). Cada trecho do contexto será prefixado com sua origem (ex: 'Fonte: NomedoDocumento.pdf, Seção: Introdução').\n\n"
        "Ao responder perguntas que apresentem alternativas (ex: a, b, c):\n"
        "- IMPERATIVO: Sua resposta DEVE respeitar OBRIGATORIAMENTE a estrutura de alternativas ou questões fornecidas na pergunta.\n"
        "- Após identificar a alternativa, forneça uma JUSTIFICATIVA BREVE E DIRETA, baseada estritamente no 'Contexto', explicando o porquê da resposta.\n"
        "- NÃO mencione alternativas que não foram fornecidas na pergunta, NÃO responda perguntas que não foram feitas.\n"
        "- MANTENHA A RESPOSTA FINAL O MAIS CURTA E OBJETIVA POSSÍVEL, respeitando o formato acima.\n\n"
        "Para todas as respostas:\n"
        "- IMPERATIVO: Fundamente TODAS as suas afirmações e conclusões estritamente nas informações presentes nos trechos do 'Contexto' fornecidos. NÃO FAÇA suposições ou inferências além do que está explicitamente escrito.\n"
        "- CITE AS FONTES: Ao usar uma informação para sua justificativa, referencie explicitamente a fonte e seção fornecida no 'Contexto' (ex: 'De acordo com NomedoDocumento.pdf, Seção Metodologia, afirma-se que...' ou '(Fonte: NomedoDocumento.pdf, Seção Resultados)'). Se a informação estiver em múltiplos trechos, cite o mais relevante ou todos, se prático.\n"
        "- Se a informação não puder ser encontrada ou confirmada de forma conclusiva e inequívoca pelo contexto fornecido, ou se o contexto for insuficiente para responder à pergunta, responda 'INCOMPLETO'. "
        "  NÃO tente responder de outra forma. Explique brevemente o motivo da incompletude (ex: 'A informação solicitada sobre X não foi encontrada nos trechos fornecidos do documento Y.', 'Os dados apresentados no contexto são insuficientes para determinar Z').\n"
        "- Responda sempre em português."
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
        """Build the user content section of the prompt."""
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