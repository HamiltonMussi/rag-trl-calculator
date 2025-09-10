# LLM configuration
import os

# LLM provider options: "local", "openai", "huggingface"
LLM_PROVIDER = "huggingface"

# Local LLM model name (HuggingFace model id)
LOCAL_LLM_MODEL_ID = "TucanoBR/Tucano-2b4-Instruct"

# OpenAI model name (e.g., "gpt-3.5-turbo", "gpt-4")
OPENAI_MODEL_NAME = "gpt-3.5-turbo"

# OpenAI API key (read from environment variable or .env)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Hugging Face Inference configuration
HF_MODEL_NAME = "Qwen/Qwen2.5-14B-Instruct:featherless-ai"  # Default HF model
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
