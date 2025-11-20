cd /Users/you/Work/Lectio

python3 -m venv .venv
source .venv/bin/activate

pip install qdrant-client requests tqdm

python3 ./python/index_corpus_qdrant.py \
  --text-dir ./corpus/text/neuroscience \
  --collection lectio_corpus \
  --ollama-url http://localhost:11434 \
  --ollama-model mxbai-embed-large \
  --qdrant-url http://localhost:6333


cd /Users/gbrouwer/Work/Lectio
source .venv/bin/activate

# point backend at the local llm-stack
export OLLAMA_URL="http://localhost:11434"
export QDRANT_URL="http://localhost:6333"
export QDRANT_COLLECTION="lectio_corpus"

python ./python/lectio_backend.py

