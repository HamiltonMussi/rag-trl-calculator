FROM continuumio/miniconda3:latest

WORKDIR /app

# Copy environment file
COPY environment.yml .

# Create conda environment
RUN conda env create -f environment.yml

# Make RUN commands use the new environment
SHELL ["conda", "run", "-n", "rag-trl-calculator", "/bin/bash", "-c"]

# Copy application code
COPY . .

# Auto-detect and install appropriate PyTorch version
RUN conda run -n rag-trl-calculator python -c "
import subprocess
import sys
try:
    # Try to detect NVIDIA GPU
    subprocess.run(['nvidia-smi'], check=True, capture_output=True)
    print('NVIDIA GPU detected, installing CUDA PyTorch...')
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'torch', '--index-url', 'https://download.pytorch.org/whl/cu121'], check=True)
except:
    print('No NVIDIA GPU detected, using CPU PyTorch...')
    # CPU version already installed via environment.yml
"

# Create directories for uploads and store if they don't exist
RUN mkdir -p uploads store

# Expose port
EXPOSE 8000

# Run the application
CMD ["conda", "run", "--no-capture-output", "-n", "rag-trl-calculator", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]