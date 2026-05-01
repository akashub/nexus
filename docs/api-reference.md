# API Reference

`nexus serve` starts a FastAPI server on `localhost:7777`. The desktop app uses this, but you can call it from anything.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/concepts` | List concepts |
| GET | `/api/concepts/:id` | Concept detail |
| POST | `/api/concepts` | Create concept (triggers enrichment) |
| PUT | `/api/concepts/:id` | Update concept |
| DELETE | `/api/concepts/:id` | Delete concept + edges |
| GET | `/api/edges?concept_id=` | List edges for a concept |
| POST | `/api/edges` | Create edge |
| DELETE | `/api/edges/:id` | Delete edge |
| GET | `/api/search?q=&semantic=` | Search (FTS or semantic) |
| POST | `/api/ask` | Ask with graph context |
| GET | `/api/graph` | Full graph (nodes + edges) |
| GET | `/api/graph/global` | Projects as nodes with shared-dep edges |
| GET | `/api/stats` | Counts and category breakdown |
| GET | `/api/projects` | List projects |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/:id` | Project detail |
| PUT | `/api/projects/:id` | Update project |
| DELETE | `/api/projects/:id` | Delete project |
| POST | `/api/projects/:id/scan` | Trigger project scan |
| POST | `/api/projects/:id/replicate` | Generate setup script |
| POST | `/api/projects/:id/compact` | Compact project graph |
| POST | `/api/projects/:id/infer-relationships` | Infer edges |
| GET | `/api/projects/:id/expertise` | Expertise profile |
| GET | `/api/concepts/:id/context` | Concept context (Eagle Mem, usage) |
| GET | `/api/journey` | Learning journey timeline |
| GET | `/api/gaps/:id` | Gap analysis for a project |
| GET | `/api/ollama/status` | Ollama availability check |
