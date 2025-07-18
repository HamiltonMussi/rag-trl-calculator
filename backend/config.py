# LLM configuration
import os

# If True, use local LLM; if False, use OpenAI API
USE_LOCAL_LLM = False

# Local LLM model name (HuggingFace model id)
LOCAL_LLM_MODEL_ID = "TucanoBR/Tucano-1b1-Instruct"

# OpenAI model name (e.g., "gpt-3.5-turbo", "gpt-4")
OPENAI_MODEL_NAME = "gpt-3.5-turbo"

# OpenAI API key (read from environment variable or .env)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Optionally, add more config as needed 