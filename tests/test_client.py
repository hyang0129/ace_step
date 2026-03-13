"""Tests for app.client — AceStepClient against a mock HTTP backend."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.client import (
    AceStepClient,
    AceStepError,
    AceStepTimeout,
    TaskResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_response(data: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        content=json.dumps(data).encode(),
        headers={"content-type": "application/json"},
    )


def _audio_response(audio: bytes = b"\x00" * 100) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        content=audio,
        headers={"content-type": "audio/wav"},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHealth:
    @pytest.mark.asyncio
    async def test_healthy(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"status": "ok"})
        )
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        assert await client.health() is True
        await client.close()

    @pytest.mark.asyncio
    async def test_unhealthy(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(500, text="error")
        )
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        assert await client.health() is False
        await client.close()


class TestGenerate:
    @pytest.mark.asyncio
    async def test_success(self):
        """Happy path: submit → poll (completed) → download audio."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            url = str(request.url)
            if "/release_task" in url:
                return _json_response(
                    {"data": {"task_id": "t-123"}, "code": 200}
                )
            elif "/query_result" in url:
                call_count += 1
                return _json_response(
                    {
                        "data": {
                            "results": [
                                {"task_id": "t-123", "status": "completed"}
                            ]
                        },
                        "code": 200,
                    }
                )
            elif "/v1/audio" in url:
                return _audio_response(b"FAKEAUDIO")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        result = await client.generate(
            description="gentle piano", duration=30
        )
        assert isinstance(result, TaskResult)
        assert result.task_id == "t-123"
        assert result.audio_bytes == b"FAKEAUDIO"
        assert result.duration_s == 30.0
        await client.close()

    @pytest.mark.asyncio
    async def test_release_task_error(self):
        transport = httpx.MockTransport(
            lambda req: _json_response(
                {"code": 500, "error": "model not loaded"}, status=200
            )
        )
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        with pytest.raises(AceStepError, match="model not loaded"):
            await client.generate(description="test")
        await client.close()

    @pytest.mark.asyncio
    async def test_task_failed(self):
        """Backend reports the task failed."""
        call_idx = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_idx
            url = str(request.url)
            if "/release_task" in url:
                return _json_response(
                    {"data": {"task_id": "t-fail"}, "code": 200}
                )
            elif "/query_result" in url:
                return _json_response(
                    {
                        "data": {
                            "results": [
                                {
                                    "task_id": "t-fail",
                                    "status": "failed",
                                    "error": "OOM",
                                }
                            ]
                        },
                        "code": 200,
                    }
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        with pytest.raises(AceStepError, match="OOM"):
            await client.generate(description="test")
        await client.close()

    @pytest.mark.asyncio
    async def test_optional_params_forwarded(self):
        """Ensure bpm, key, time_signature make it into the payload."""
        captured_body = {}

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/release_task" in url:
                captured_body.update(json.loads(request.content))
                return _json_response(
                    {"data": {"task_id": "t-opt"}, "code": 200}
                )
            elif "/query_result" in url:
                return _json_response(
                    {
                        "data": {
                            "results": [
                                {"task_id": "t-opt", "status": "completed"}
                            ]
                        },
                        "code": 200,
                    }
                )
            elif "/v1/audio" in url:
                return _audio_response()
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        await client.generate(
            description="test",
            bpm=120,
            key="Am",
            time_signature=3,
        )
        params = captured_body["params"]
        assert params["bpm"] == 120
        assert params["keyscale"] == "Am"
        assert params["timesignature"] == 3
        await client.close()
