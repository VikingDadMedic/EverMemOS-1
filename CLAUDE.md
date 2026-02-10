# CLAUDE.md

Refer to [AGENTS.md](AGENTS.md) for comprehensive project documentation including:
- Project architecture and structure
- Tech stack and dependencies
- Code conventions and patterns
- Key abstractions and files
- Development guidelines
- Database schema

## Quick Commands

```bash
docker-compose up -d          # Start infrastructure
uv sync                       # Install dependencies
make run                      # Run application
pytest                        # Run tests
black src/ && isort src/      # Format code
pyright                       # Type check
```

## Key Entry Points

- `src/run.py` - Application entry
- `src/agentic_layer/memory_manager.py` - Core memory manager
- `src/infra_layer/adapters/input/api/` - REST API controllers

## Omega Layer

- `src/omega_layer/` - Cognitive substrate for Omega entity
- `OMEGA_MODE=true` in `.env` to enable Pentagram processing
- `POST /api/v1/omega/process` - Route experience through 5 vertices + kernel
- `GET /api/v1/omega/development` - Check growth level
- `GET /api/v1/omega/identity` - View identity topology state
- Identity DNA: `src/omega_layer/identity/omega_scar.json`
- Run omega tests: `pytest tests/test_omega_*.py -v`

## Remember

- All I/O is async - use `await`
- Multi-tenant system - data is tenant-scoped
- Prompts in `src/memory_layer/prompts/` (EN/ZH)
- Omega prompts in `src/omega_layer/prompts/en/`
- omega_layer is ADDITIVE - never modify existing EverMemOS core files
