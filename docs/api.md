# ACE-Step Client Library — Reference

## Client

```python
from app.client import AceStepClient, TaskResult, AceStepError, AceStepTimeout
```

### AceStepClient

| Method | Description |
|--------|-------------|
| `__init__(base_url)` | Create client pointing at ACE-Step server |
| `await health()` | Returns `True` if backend is reachable |
| `await generate(**kwargs)` | Submit, poll, download — returns `TaskResult` |
| `await close()` | Shut down the httpx session |

### generate() parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `description` | str | *required* | Natural-language style prompt |
| `duration` | int | 30 | Length in seconds (10–600) |
| `instrumental` | bool | True | Instrumental only (no vocals) |
| `bpm` | int \| None | None | Beats per minute (auto if None) |
| `key` | str \| None | None | Musical key, e.g. `"C Major"`, `"Am"` |
| `time_signature` | int \| None | None | 2, 3, 4, or 6 (auto if None) |
| `guidance_scale` | float | 7.0 | Prompt adherence (1.0–15.0) |
| `num_inference_steps` | int | 8 | Diffusion steps (turbo: 1–20) |
| `seed` | int | -1 | Reproducibility seed (-1 = random) |
| `audio_format` | str | "wav" | `"wav"` or `"mp3"` |

### TaskResult

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | str | ACE-Step task identifier |
| `audio_bytes` | bytes | Raw audio data |
| `duration_s` | float | Audio duration in seconds |
| `sample_rate` | int | Sample rate (44100) |
| `format` | str | `"wav"` or `"mp3"` |

## Presets

```python
from app.presets import get_preset, list_presets
```

| Function | Returns | Description |
|----------|---------|-------------|
| `get_preset(id)` | `PresetInfo \| None` | Lookup by ID |
| `list_presets()` | `list[PresetInfo]` | All presets, sorted by ID |

### Available presets

| ID | BPM | Use case |
|----|-----|----------|
| `documentary_ambient` | 80 | Reflective, atmospheric |
| `history_epic` | 100 | Grand orchestral, historical |
| `biography_warm` | 90 | Intimate piano, nostalgic |
| `science_curiosity` | 110 | Playful electronic, educational |
| `investigation_tension` | 70 | Dark, suspenseful |
| `travel_upbeat` | 120 | Cheerful, adventure |
| `economics_neutral` | 95 | Minimal, corporate/news |
| `nature_peaceful` | 75 | Serene, pastoral |
