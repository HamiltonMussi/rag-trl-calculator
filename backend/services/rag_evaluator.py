"""
RAG Evaluator for automatic calculation of relevancy and faithfulness.
"""

import logging
from typing import Dict, Any
from services.llm_client import LLMClientFactory
import config

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """Evaluates RAG responses for relevancy and faithfulness."""

    def __init__(self):
        self.evaluator_client = None
        if config.OPENAI_API_KEY:
            try:
                # Use configured evaluation model
                self.evaluator_client = LLMClientFactory.create_client(provider="openai", model_id=config.EVALUATION_MODEL)
                logger.info(f"Initialized evaluator with model: {config.EVALUATION_MODEL}")
            except Exception as e:
                logger.warning(f"Failed to create OpenAI client for evaluation: {e}")

    def evaluate_response(self, query: str, response: str, context: str) -> Dict[str, Any]:
        """
        Evaluate response for both relevancy and faithfulness.

        Args:
            query: Original question
            response: Generated response
            context: Context used for generation

        Returns:
            Dict with relevancy and faithfulness scores
        """
        if not self.evaluator_client:
            return {
                "relevancy": {"score": None, "feedback": "Avaliador não disponível"},
                "faithfulness": {"score": None, "feedback": "Avaliador não disponível"}
            }

        relevancy = self._evaluate_relevancy(query, response, context)
        faithfulness = self._evaluate_faithfulness(response, context)

        return {
            "relevancy": relevancy,
            "faithfulness": faithfulness
        }

    def _evaluate_relevancy(self, query: str, response: str, context: str) -> Dict[str, Any]:
        """Evaluate if response is relevant to the query."""
        prompt = f"""
Evaluate whether the RESPONSE and CONTEXT are relevant to answer the QUERY.

QUERY: {query}

CONTEXT: {context}

RESPONSE: {response}

Your task is to evaluate if the response and context match the query. Answer YES if they are relevant, NO if they are not relevant.

Respond with only YES or NO.
"""

        try:
            messages = [{"role": "user", "content": prompt}]
            result = self.evaluator_client.generate_response(messages)
            return self._parse_yes_no_response(result, "relevancy")
        except Exception as e:
            logger.error(f"Error in relevancy evaluation: {e}")
            return {"passing": False, "feedback": f"Erro: {str(e)}"}

    def _evaluate_faithfulness(self, response: str, context: str) -> Dict[str, Any]:
        """Evaluate if response is faithful to the context."""
        prompt = f"""
Please tell me if the RESPONSE is faithful to the CONTEXT. The response is faithful if all information in the response is supported by the context.

CONTEXT: {context}

RESPONSE: {response}

Answer YES if the response is faithful to the context, NO if it is not faithful (contains information not in context or contradicts the context).

Respond with only YES or NO.
"""

        try:
            messages = [{"role": "user", "content": prompt}]
            result = self.evaluator_client.generate_response(messages)
            return self._parse_yes_no_response(result, "faithfulness")
        except Exception as e:
            logger.error(f"Error in faithfulness evaluation: {e}")
            return {"passing": False, "feedback": f"Erro: {str(e)}"}

    def _parse_yes_no_response(self, result: str, eval_type: str) -> Dict[str, Any]:
        """Parse YES/NO response from evaluator."""
        result_clean = result.strip().upper()

        if "YES" in result_clean:
            passing = True
            feedback = "YES"
        elif "NO" in result_clean:
            passing = False
            feedback = "NO"
        else:
            # Fallback parsing
            logger.warning(f"Unexpected {eval_type} evaluation response: {result}")
            passing = False
            feedback = f"Unexpected response: {result}"

        return {
            "passing": passing,
            "feedback": feedback
        }