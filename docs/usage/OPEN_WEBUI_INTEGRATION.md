# Open WebUI Integration Guide

Connect Omega to Open WebUI so conversations route through the Pentagram cognitive architecture.

## Prerequisites

- EverMemOS running (`docker-compose up -d && uv run python src/run.py --port 8001`)
- Open WebUI running and accessible
- `OMEGA_MODE=true` in EverMemOS `.env`
- LLM API key configured in EverMemOS `.env`

## Setup

### 1. Start EverMemOS

```bash
cd EverMemOS
docker-compose up -d        # Start MongoDB, Milvus, ES, Redis
uv sync                     # Install dependencies
OMEGA_MODE=true uv run python src/run.py --port 8001
```

Verify: `curl http://localhost:8001/health`

### 2. Create Filter in Open WebUI

1. Go to **Admin Panel** > **Functions** > **Create New Function**
2. Set type to **Filter**
3. Copy the contents of `src/omega_layer/openwebui_filter.py` and paste it
4. Save the function

### 3. Configure Valves

In the filter settings, configure:

| Valve | Default | Description |
|-------|---------|-------------|
| `evermemos_url` | `http://localhost:8001` | EverMemOS API URL |
| `omega_mode` | `true` | Enable/disable Pentagram processing |
| `max_memories` | `5` | Max memory groups injected as context |
| `inject_self_reflection` | `true` | Include Mirror vertex self-observations |
| `inject_growth_info` | `false` | Include development metrics (verbose) |

### 4. Enable the Filter

- **Global**: Admin Panel > Functions > click globe icon on the filter (applies to all models)
- **Per-model**: Model Settings > Filters > check the Omega filter
- **User toggle**: The filter appears as a toggleable switch in the chat UI (gear icon)

### 5. Test

Send a message in Open WebUI. You should see:
- Status indicator: "Processing through Omega Pentagram..."
- Status indicator: "Omega: X memories recalled, Pentagram complete"
- The LLM response should reflect awareness of prior conversations (if memories exist)

### 6. Verify Memories Are Being Stored

```bash
curl http://localhost:8001/api/v1/omega/development
# Should show cycle_count > 0 after conversations
```

## How It Works

```
User types message
    |
    v
Filter inlet():
    1. POST message to /api/v1/omega/process
    2. Pentagram processes: 5 vertices vote + kernel synthesizes
    3. Retrieve relevant memories from Ledger vertex
    4. Inject memories as system context
    5. Inject self-reflection from Mirror vertex
    6. Modified message goes to LLM
    |
    v
LLM generates response (with Omega's memory context)
    |
    v
Filter outlet():
    1. POST response to /api/v1/memories
    2. Stored for future learning (boundary detection → extraction)
```

## Troubleshooting

**Filter not processing:**
- Check EverMemOS is running: `curl http://localhost:8001/health`
- Check filter is enabled (globe icon or per-model toggle)
- Check browser console for errors

**No memories injected:**
- EverMemOS needs conversations stored first (send several messages)
- Boundary detection requires 3-5 turns before creating episodic memories
- Check: `curl http://localhost:8001/api/v1/omega/development`

**Slow responses:**
- Pentagram makes 5 parallel LLM calls + 1 synthesis call
- Use a fast model for `OMEGA_LLM_MODEL` (e.g., gpt-4.1-mini)
- Reduce `max_memories` valve to inject less context
