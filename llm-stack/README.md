# LLM Stack: Ollama + AnythingLLM + Qdrant

This directory defines a local, Docker-based stack for:

- **Ollama** – local LLM + embedding model hosting
- **Qdrant** – vector database for document embeddings
- **AnythingLLM** – UI/orchestrator that can talk to both

## Prerequisites

- Docker Desktop installed and running
- Enough disk space for models and vector data

## Start the stack

From the `llm-stack` directory:

```bash
cd llm-stack
docker compose up -d
```

This will start:

- Ollama on `http://localhost:11434`
- Qdrant on `http://localhost:6333`
- AnythingLLM Web UI on `http://localhost:3001`

## First-time setup

1. **Open AnythingLLM**  
   Go to `http://localhost:3001` in your browser and follow the onboarding flow.

2. **Configure Ollama in AnythingLLM**  
   - Set the Ollama base URL to `http://ollama:11434` inside the container (the compose file already wires this).
   - Pull at least one model in Ollama (e.g. from your host shell: `ollama pull mistral` or any model you want).

3. **Configure Qdrant as the vector DB**  
   - Choose Qdrant as the vector database in AnythingLLM.
   - The compose file already sets `VECTOR_DB=qdrant` and `QDRANT_URL=http://qdrant:6333`.

Once this is done, AnythingLLM will use:

- Ollama for LLM and embedding generation
- Qdrant for storing and querying embeddings

Your Python tools in this repo can also talk directly to Qdrant at `http://localhost:6333` for corpus-level experiments.

