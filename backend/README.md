# RAG-TRL Calculator Backend

Backend API for Technology Readiness Level (TRL) assessment using Retrieval-Augmented Generation (RAG).

## Quick Start

### 1. Environment Setup

```bash
# Create conda environment
conda env create -f environment.yml
conda activate rag-trl-calculator

# Configure API keys
cp .env.example .env
# Edit .env with your API keys
```

### 2. Run the Server

```bash
python main.py
```

Server runs at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## Configuration

Edit `config.py`:

| Variable | Options | Default | Description |
|----------|---------|---------|-------------|
| `LLM_PROVIDER` | `openai`, `huggingface`, `local` | `openai` | LLM provider |
| `OPENAI_MODEL_NAME` | `gpt-3.5-turbo`, `gpt-4`, etc. | `gpt-3.5-turbo` | OpenAI model |
| `HF_MODEL_NAME` | Any HuggingFace model | `Qwen/Qwen2.5-14B-Instruct` | HuggingFace model |
| `ENABLE_RAG` | `true`, `false` | `true` | Enable document retrieval |
| `ENABLE_PROMPT_ENGINEERING` | `true`, `false` | `true` | Apply prompt techniques |
| `ENABLE_EVALUATION` | `true`, `false` | `false` | Auto-evaluate responses |
| `EVALUATION_MODEL` | Any OpenAI model | `gpt-4o-mini` | Model for evaluation |

## API Endpoints

### Upload Documents
```bash
POST /upload-files
```
Upload PDF/TXT/MD documents for a technology.

### Set Technology Context
```bash
POST /set-technology-context
```
Set the active technology for the session.

### Ask Questions
```bash
POST /answer
```
Generate TRL assessment answers using RAG.

### Manage Files
```bash
GET /list-files          # List uploaded files
DELETE /remove-file      # Remove a file
GET /status             # Check processing status
```

## Project Structure

```
backend/
├── api/                    # FastAPI routes and schemas
├── services/               # Business logic
│   ├── chromadb_service.py    # Vector database
│   ├── document_service.py    # Document chunking
│   ├── llm_client.py          # LLM abstraction
│   ├── rag_evaluator.py       # Response evaluation
│   └── ...
├── retrieval/              # Context retrieval
├── processing/             # Document indexing
├── utils/                  # Utilities
├── data/                   # TRL glossary data
├── store/                  # ChromaDB storage
├── main.py                 # Entry point
└── config.py              # Configuration
```

## Evaluation Metrics

When `ENABLE_EVALUATION=true`, responses are automatically evaluated:

- **Relevancy**: Is the response relevant to the query?
- **Faithfulness**: Is the response accurate to the context?

Both metrics return `YES/NO` using GPT-4o-mini as evaluator.

## Development

See `ARCHITECTURE.md` for detailed architecture documentation.

See `TESTS.md` for testing framework documentation.

## Requirements

- Python 3.11+
- Conda environment manager
- OpenAI API key (for OpenAI models and evaluation)
- HuggingFace API token (optional, for HF models)
