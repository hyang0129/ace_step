"""Async client for the ACE-Step v1.5 built-in API server.

ACE-Step exposes a task-based REST API (default http://localhost:8001).
This client wraps the submit → poll → download flow behind a single
async method so the FastAPI layer can offer a synchronous-feeling endpoint.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ACESTEP_BASE_URL = os.environ.get("ACESTEP_BASE_URL", "http://localhost:8001")
POLL_INTERVAL_S = float(os.environ.get("ACESTEP_POLL_INTERVAL", "1.0"))
POLL_TIMEOUT_S = float(os.environ.get("ACESTEP_POLL_TIMEOUT", "300"))


class AceStepError(Exception):
    """Raised when the ACE-Step backend returns an error."""


class AceStepTimeout(AceStepError):
    """Raised when polling for a task result exceeds the timeout."""


@dataclass(slots=True)
class TaskResult:
    """Resolved result from ACE-Step."""

    task_id: str
    audio_bytes: bytes
    duration_s: float
    sample_rate: int
    format: str


class AceStepClient:
    """Thin async wrapper around ACE-Step's REST API.

    Lifecycle: create once during app lifespan, close on shutdown.
    """

    def __init__(self, base_url: str = ACESTEP_BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    # -- health -----------------------------------------------------------

    async def health(self) -> bool:
        """Return *True* if the ACE-Step server is reachable."""
        try:
            resp = await self._http.get("/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    # -- generation -------------------------------------------------------

    async def generate(
        self,
        *,
        description: str,
        duration: int = 30,
        instrumental: bool = True,
        bpm: int | None = None,
        key: str | None = None,
        time_signature: int | None = None,
        guidance_scale: float = 7.0,
        num_inference_steps: int = 8,
        seed: int = -1,
        audio_format: str = "wav",
    ) -> TaskResult:
        """Submit a generation task, poll until complete, return audio bytes."""

        # 1. Build the payload for ACE-Step's /release_task
        payload: dict[str, Any] = {
            "task_type": "generate",
            "params": {
                "caption": description,
                "duration": duration,
                "instrumental": instrumental,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "seed": seed,
                "audio_format": audio_format,
            },
        }
        if bpm is not None:
            payload["params"]["bpm"] = bpm
        if key is not None:
            payload["params"]["keyscale"] = key
        if time_signature is not None:
            payload["params"]["timesignature"] = time_signature

        # 2. Submit
        resp = await self._http.post("/release_task", json=payload)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != 200:
            raise AceStepError(f"release_task failed: {body.get('error')}")
        task_id: str = body["data"]["task_id"]
        logger.info("Submitted task %s", task_id)

        # 3. Poll for completion
        audio_bytes = await self._poll_task(task_id, audio_format)

        return TaskResult(
            task_id=task_id,
            audio_bytes=audio_bytes,
            duration_s=float(duration),
            sample_rate=44100,
            format=audio_format,
        )

    # -- internals --------------------------------------------------------

    async def _poll_task(self, task_id: str, audio_format: str) -> bytes:
        """Poll /query_result until task completes, then download audio."""
        elapsed = 0.0
        while elapsed < POLL_TIMEOUT_S:
            resp = await self._http.post(
                "/query_result", json={"task_ids": [task_id]}
            )
            resp.raise_for_status()
            body = resp.json()
            if body.get("code") != 200:
                raise AceStepError(f"query_result error: {body.get('error')}")

            results = body["data"].get("results", [])
            if results and results[0].get("status") == "completed":
                return await self._download_audio(task_id, audio_format)
            if results and results[0].get("status") == "failed":
                raise AceStepError(
                    f"Task {task_id} failed: {results[0].get('error', 'unknown')}"
                )

            await asyncio.sleep(POLL_INTERVAL_S)
            elapsed += POLL_INTERVAL_S

        raise AceStepTimeout(
            f"Task {task_id} did not complete within {POLL_TIMEOUT_S}s"
        )

    async def _download_audio(self, task_id: str, audio_format: str) -> bytes:
        """Download the generated audio file from ACE-Step."""
        resp = await self._http.get(
            "/v1/audio", params={"task_id": task_id, "format": audio_format}
        )
        resp.raise_for_status()
        return resp.content

    # -- lifecycle --------------------------------------------------------

    async def close(self) -> None:
        await self._http.aclose()
