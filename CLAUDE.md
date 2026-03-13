# ACE-Step Client Library

## Overview

Client library and presets module for ACE-Step v1.5 music generation.
Talks directly to ACE-Step's built-in API server (`acestep-api`).
Consumed by `video_agent` and potentially other repos in this workspace.

## Architecture

- **ACE-Step server** (port 8001): runs model inference via `acestep-api`
- **This library**: async httpx client + documentary music presets
- `video_agent` imports `ace_step.client` and `ace_step.presets` directly

## Key Constraints

- Python 3.11, type hints throughout
- Line length 100 (ruff)
- Venv: `/workspaces/.venvs/ace_step/`

## Usage

```python
from app.client import AceStepClient
from app.presets import get_preset

client = AceStepClient(base_url="http://localhost:8001")
preset = get_preset("documentary_ambient")

result = await client.generate(
    description=preset.description,
    duration=preset.duration,
    bpm=preset.bpm,
    instrumental=True,
)
# result.audio_bytes contains the WAV/MP3 data
await client.close()
```

## Testing

```bash
source /workspaces/.venvs/ace_step/bin/activate
pytest
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ACESTEP_BASE_URL` | `http://localhost:8001` | ACE-Step server URL |
| `ACESTEP_POLL_INTERVAL` | `1.0` | Seconds between status polls |
| `ACESTEP_POLL_TIMEOUT` | `300` | Max seconds to wait for generation |

## Forked ACE-Step

We maintain a forked copy of ACE-Step v1.5 for stability and customization.
Upstream: https://github.com/ace-step/ACE-Step-1.5
