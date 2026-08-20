"""Responsible, cached access to SEC EDGAR resources."""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import json


class SecClient:
    """Download SEC resources while identifying, rate-limiting, and caching requests."""

    def __init__(
        self,
        user_agent: str,
        cache_dir: Path,
        requests_per_second: float = 5.0,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.minimum_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0

        self.stats = {
            "requests_sent": 0,
            "cache_hits": 0,
            "files_downloaded": 0,
        }

        self.client = httpx.Client(
            headers={
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            follow_redirects=True,
            timeout=30.0,
        )


    def _wait_for_rate_limit(self) -> None:
        """Wait long enough to remain below the configured request rate."""
        elapsed = time.monotonic() - self.last_request_time
        remaining = self.minimum_interval - elapsed

        if remaining > 0:
            time.sleep(remaining)


    def get_bytes(self, url: str, cache_key: str) -> bytes:
        """Return a resource from cache, or download and cache it."""
        cache_path = self.cache_dir / cache_key

        if cache_path.exists():
            self.stats["cache_hits"] += 1
            return cache_path.read_bytes()

        cache_path.parent.mkdir(parents=True, exist_ok=True)

        retryable_statuses = {403, 429, 500, 502, 503, 504}
        maximum_attempts = 5

        for attempt in range(maximum_attempts):
            self._wait_for_rate_limit()
            self.last_request_time = time.monotonic()
            self.stats["requests_sent"] += 1

            try:
                response = self.client.get(url)
            except httpx.RequestError:
                if attempt == maximum_attempts - 1:
                    raise

                time.sleep(2 ** attempt)
                continue

            if response.status_code in retryable_statuses:
                if attempt == maximum_attempts - 1:
                    response.raise_for_status()

                time.sleep(2 ** attempt)
                continue

            response.raise_for_status()

            temporary_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
            temporary_path.write_bytes(response.content)
            temporary_path.replace(cache_path)

            self.stats["files_downloaded"] += 1
            return response.content

        raise RuntimeError(f"Failed to download {url}")


    def get_text(self, url: str, cache_key: str) -> str:
        """Return a downloaded resource as text."""
        return self.get_bytes(url, cache_key).decode("utf-8", errors="replace")

    def get_json(self, url: str, cache_key: str):
        """Return a downloaded JSON resource as Python objects."""
        return json.loads(self.get_bytes(url, cache_key))

    def write_manifest(self, path: Path) -> None:
        """Write request and cache statistics for the current run."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.stats, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def close(self) -> None:
        """Close the reusable HTTP connection."""
        self.client.close()