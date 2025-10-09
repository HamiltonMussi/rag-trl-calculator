# RAG-TRL Calculator

AI-powered Technology Readiness Level (TRL) assessment system using Retrieval-Augmented Generation (RAG).

## About

This project was developed as a final course project (Projeto de Final de Curso) for the Computer Engineering program at Instituto Militar de Engenharia (IME), class of 2025.

**Developers:**
- Hamilton Mussi Corrêa Filho
- Pedro Henrique Gallio Bulcão

## Overview

This system consists of two main components:
- **Backend**: FastAPI-based RAG system for document processing and AI-powered TRL assessment
- **Extension**: Chrome extension that integrates with the existing TRL calculator web application

## Project Structure

```
rag-trl-calculator/
├── backend/              # RAG API backend
│   ├── api/             # FastAPI routes and schemas
│   ├── services/        # Business logic
│   ├── retrieval/       # Context retrieval
│   ├── processing/      # Document processing
│   ├── utils/           # Utilities
│   ├── data/            # TRL glossary data
│   └── README.md        # Backend documentation
└── extension/           # Chrome extension
    ├── src/            # Extension source code
    ├── assets/         # Icons and resources
    └── README.md       # Extension documentation
```

## Quick Start

### Backend Setup

```bash
cd backend

# Create conda environment
conda env create -f environment.yml
conda activate rag-trl-calculator

# Configure API keys
cp .env.example .env
# Edit .env with your OpenAI and HuggingFace API keys

# Run server
python main.py
```

Server runs at `http://localhost:8000`

### Extension Installation

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `extension` directory
4. The extension is now ready to use with the TRL calculator web application

## Features

### Backend
- **RAG System**: Document-based context retrieval for accurate TRL assessments
- **Multi-LLM Support**: OpenAI (GPT-3.5, GPT-4), HuggingFace (Qwen, Gemma), and local models
- **Automated Evaluation**: Relevancy and faithfulness metrics for response quality
- **Document Processing**: Intelligent chunking with section awareness for academic papers
- **Vector Database**: ChromaDB for efficient semantic search

### Extension
- **AI-Powered Assistance**: Get intelligent suggestions for TRL questionnaire answers
- **Document Management**: Upload and manage technology documentation
- **Multi-page Support**: Works across all stages of the TRL assessment
- **Modern Architecture**: ES6+ modules, accessibility compliant, responsive design

## Configuration

Backend configuration in `backend/config.py`:

| Variable | Options | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai`, `huggingface`, `local` | LLM provider selection |
| `ENABLE_RAG` | `true`, `false` | Enable/disable document retrieval |
| `ENABLE_PROMPT_ENGINEERING` | `true`, `false` | Apply prompt engineering techniques |
| `ENABLE_EVALUATION` | `true`, `false` | Auto-evaluate responses |

See `backend/README.md` for detailed configuration options.

## Documentation

- **Backend Architecture**: `backend/ARCHITECTURE.md`
- **Testing Framework**: `backend/TESTS.md`
- **Backend API**: `backend/README.md`
- **Extension Guide**: `extension/README.md`

## Requirements

- Python 3.11+
- Conda environment manager
- OpenAI API key (for OpenAI models and evaluation)
- HuggingFace API token (optional, for HuggingFace models)
- Chrome browser (for extension)

## API Endpoints

- `POST /upload-files` - Upload technology documents
- `POST /set-technology-context` - Set active technology
- `POST /answer` - Generate TRL assessment answers
- `POST /list-files` - List uploaded documents
- `POST /remove-file` - Remove documents
- `POST /status` - Check processing status

Full API documentation available at `http://localhost:8000/docs` when server is running.
