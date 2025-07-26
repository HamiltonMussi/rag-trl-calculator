# RAG-TRL Calculator Backend Architecture

## Overview

This document describes the refactored architecture of the RAG-TRL Calculator backend, which implements a Retrieval-Augmented Generation (RAG) system for Technology Readiness Level (TRL) analysis.

## Architecture Principles

The refactoring follows these key principles:

- **Single Responsibility**: Each service/class has one clear purpose
- **Dependency Injection**: Services are loosely coupled and testable
- **Error Handling**: Comprehensive error handling with structured error types
- **Separation of Concerns**: Clear separation between API, business logic, and data access
- **Modularity**: Code is organized into logical modules and services

## Directory Structure

```
backend/
├── api/                    # API layer
│   ├── routes.py          # FastAPI route handlers
│   └── schemas.py         # Pydantic models for API contracts
├── services/               # Business logic services
│   ├── chromadb_service.py    # ChromaDB operations
│   ├── document_service.py    # Document processing and chunking
│   ├── error_handler.py       # Centralized error handling
│   ├── session_manager.py     # Session management
│   ├── llm_client.py          # LLM client abstraction
│   ├── prompt_builder.py      # Prompt construction
│   └── validation.py          # Input validation
├── processing/             # Document processing
│   ├── indexer.py             # Document indexing orchestration
│   └── document_processor.py  # DEPRECATED: Legacy processor
├── retrieval/              # Information retrieval
│   └── context_retriever.py  # Context search and retrieval
├── utils/                  # Utility functions
│   ├── file_utils.py          # File processing utilities
│   ├── hf_models.py           # HuggingFace model utilities
│   └── logging_config.py      # Logging configuration
├── main.py                 # Application entry point
└── config.py              # Configuration settings
```

## Core Services

### 1. ChromaDBService (`services/chromadb_service.py`)

Centralizes all ChromaDB operations:
- Collection management (technology-specific and TRL collections)
- Document chunk storage and retrieval
- Query operations with embedding search
- Error handling for database operations

**Key Methods:**
- `get_technology_collection(tech_id)`: Get/create technology collection
- `add_document_chunks()`: Store document chunks with embeddings
- `remove_document_chunks()`: Remove chunks for a specific file
- `query_collection()`: Search collection with embeddings

### 2. DocumentService (`services/document_service.py`)

Handles document processing and chunking:
- **DocumentChunker**: Creates semantic chunks with section awareness
- **DocumentProcessor**: Main document processing orchestration
- Supports academic document structure (abstract, introduction, methodology, etc.)
- Token-aware chunking using LLM tokenizer

**Key Features:**
- Section-aware chunking for academic documents
- Configurable chunk sizes and overlap
- Metadata enrichment for each chunk
- Fallback handling for unstructured documents

### 3. ErrorHandler (`services/error_handler.py`)

Comprehensive error handling system:
- **ApplicationError**: Structured error representation
- **ErrorCode**: Enumerated error types
- **ValidationService**: Input validation with detailed error messages
- Consistent error formatting across the application

**Error Categories:**
- Validation errors (invalid input, missing fields)
- File processing errors (unsupported types, read failures)
- Database errors (connection issues, operation failures)
- Processing errors (chunking, embedding generation)
- LLM errors (generation failures, configuration issues)

### 4. FileProcessor (`utils/file_utils.py`)

File handling utilities:
- Support for PDF, TXT, and MD files
- Multiple encoding fallbacks for text files
- Clean error handling and reporting
- Utility functions for safe filename generation

## API Layer

### Route Organization

The API routes (`api/routes.py`) are organized around these main operations:

1. **File Upload** (`/upload-files`): Upload and process documents
2. **Processing Status** (`/status`): Check document processing status
3. **Technology Context** (`/set-technology-context`): Set session context
4. **Question Answering** (`/answer`): Generate answers using RAG
5. **File Management** (`/list-files`, `/remove-file`): Manage uploaded files

### Request/Response Flow

1. **Input Validation**: All inputs validated using `ValidationService`
2. **Error Handling**: Standardized error responses using `ErrorHandler`
3. **Business Logic**: Delegates to appropriate services
4. **Response Formatting**: Consistent response structure using Pydantic schemas

## Data Flow

### Document Processing Flow

```
File Upload → FileProcessor → DocumentProcessor → ChromaDBService
     ↓              ↓              ↓                    ↓
Base64 Decode → Text Extract → Semantic Chunks → Store w/ Embeddings
```

### Question Answering Flow

```
Question → Context Retrieval → Prompt Building → LLM Generation → Response
    ↓            ↓                   ↓               ↓            ↓
Validate → Search Collections → Build Messages → Generate → Format
```

## Error Handling Strategy

### Error Types

1. **Client Errors (4xx)**:
   - Validation failures
   - Missing required fields
   - Unsupported file types
   - Session not found

2. **Server Errors (5xx)**:
   - Database connection issues
   - LLM generation failures
   - File processing errors
   - Internal service errors

### Error Response Format

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "context": {
    "additional": "context information"
  }
}
```

## Logging Strategy

### Structured Logging

- **Context-aware logging**: Each service can add context to log messages
- **Centralized configuration**: Single logging setup in `utils/logging_config.py`
- **External library filtering**: Reduced verbosity from third-party libraries
- **File rotation**: Automatic log file rotation with size limits

### Log Levels

- **DEBUG**: Detailed debugging information (disabled in production)
- **INFO**: General operational messages
- **WARNING**: Potentially problematic situations
- **ERROR**: Error conditions that don't stop the application
- **CRITICAL**: Serious errors that may cause application shutdown

## Configuration Management

Configuration is centralized in `config.py`:

- **LLM Settings**: Local vs. OpenAI, model selection
- **API Keys**: Secure handling of external service keys
- **Model Parameters**: Tokenization and generation settings
- **Environment Variables**: Support for .env files

## Testing Strategy

The refactored architecture supports testing through:

1. **Service Isolation**: Each service can be tested independently
2. **Dependency Injection**: Easy mocking of dependencies
3. **Error Simulation**: Structured errors enable comprehensive error testing
4. **Pure Functions**: Many utility functions are pure and easily testable

## Performance Considerations

### Optimization Features

1. **Lazy Loading**: Models loaded only when needed
2. **Caching**: LRU cache for expensive operations
3. **Device Management**: Optimal GPU/CPU device selection
4. **Connection Pooling**: Efficient database connection reuse
5. **Token Counting**: Accurate token-based chunking

### Scalability

- **Stateless Services**: Most services are stateless and horizontally scalable
- **Session Management**: Lightweight session tracking with cleanup
- **Resource Management**: Proper cleanup and resource deallocation

## Security Considerations

1. **Input Validation**: Comprehensive validation of all inputs
2. **File Type Restrictions**: Only allowed file types accepted
3. **Error Information**: No sensitive information leaked in error messages
4. **Session Security**: Session IDs properly validated
5. **API Key Protection**: Secure handling of external API keys

## Migration Notes

### Backward Compatibility

- Legacy functions maintained in `processing/document_processor.py`
- Existing API contracts preserved
- Database schema unchanged

### Deprecated Components

- `create_semantic_chunks()` in `document_processor.py` → Use `DocumentProcessor`
- Direct ChromaDB client usage → Use `ChromaDBService`
- Manual error handling → Use `ErrorHandler`

## Future Enhancements

1. **Metrics and Monitoring**: Add application metrics and health checks
2. **Caching Layer**: Implement Redis for response caching
3. **Async Processing**: Convert blocking operations to async
4. **API Versioning**: Support multiple API versions
5. **Enhanced Security**: Add authentication and rate limiting