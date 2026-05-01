# Configuration

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXUS_LLM_MODEL` | `gemma3` | Ollama model for text generation. Any model works — `llama3`, `mistral`, `phi3`, `gemma3`, etc. |
| `NEXUS_EMBED_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `ANTHROPIC_API_KEY` | — | Enable cloud enrichment via Anthropic |
| `OPENAI_API_KEY` | — | Enable cloud enrichment via OpenAI |

## AI Models

Nexus works with **any Ollama model**. The default (`gemma3`) is a good balance of speed and quality. To use a different model:

```bash
# Set globally
export NEXUS_LLM_MODEL=llama3

# Or per-command
NEXUS_LLM_MODEL=mistral nexus add "React"
```

Popular choices:
- `gemma3` — fast, good for enrichment (default)
- `gemma4` — higher quality, slower
- `llama3` — good general-purpose alternative
- `mistral` — fast, compact

Ollama is optional. Everything works without it — you just won't get AI-generated descriptions, summaries, or embeddings. Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` for cloud-based enrichment instead.

## Database

SQLite with WAL mode at `~/.nexus/nexus.db`. Migrations in `backend/migrations/`, applied automatically on `nexus db init` and server startup.

## Desktop App

The desktop app connects to the API server at `localhost:7777`. Start it with:

```bash
nexus serve
```

The Tauri app auto-starts the server on launch if it's not already running.
