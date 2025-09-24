# Testing Framework

## Overview

The RAG-TRL Calculator implements automated evaluation of RAG responses through the `RAGEvaluator` service, which assesses response quality using two key metrics.

## Evaluation Metrics

### Relevancy Testing
- **Purpose**: Evaluates if the response and context are relevant to answer the original query
- **Method**: Uses OpenAI's evaluation model to determine YES/NO relevancy
- **Implementation**: `_evaluate_relevancy()` in `services/rag_evaluator.py`

### Faithfulness Testing
- **Purpose**: Evaluates if the response is faithful to the provided context
- **Method**: Checks if all information in the response is supported by the context
- **Implementation**: `_evaluate_faithfulness()` in `services/rag_evaluator.py`

## Test Configuration

```python
# Configuration in config.py
ENABLE_EVALUATION = os.getenv("ENABLE_EVALUATION", "true").lower() == "true"
EVALUATION_MODEL = os.getenv("EVALUATION_MODEL", "gpt-4o-mini")
```

## Test Execution Flow

1. **Response Generation**: Main LLM generates response using RAG context
2. **Evaluation Trigger**: If `ENABLE_EVALUATION=true`, evaluator is called
3. **Relevancy Check**: Evaluates query-response-context alignment
4. **Faithfulness Check**: Verifies response fidelity to source context
5. **Results Logging**: Pass/fail results logged for analysis

## Test Results Format

```python
{
    "relevancy": {
        "passing": true/false,
        "feedback": "YES/NO or error message"
    },
    "faithfulness": {
        "passing": true/false,
        "feedback": "YES/NO or error message"
    }
}
```

## Integration Points

- **API Route**: `/answer` endpoint automatically runs evaluation when enabled
- **Error Handling**: Graceful degradation when evaluator unavailable
- **Logging**: Detailed evaluation results logged for monitoring
- **Dependencies**: Requires OpenAI API key for evaluation model access

## Usage

Enable evaluation by setting environment variable:
```bash
export ENABLE_EVALUATION=true
export EVALUATION_MODEL=gpt-4o-mini
```

Evaluation runs automatically on each `/answer` request when enabled.