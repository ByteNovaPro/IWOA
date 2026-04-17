from __future__ import annotations

import os
from typing import Any

import httpx

from app.config import load_settings


class BackendClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("BACKEND_BASE_URL") or load_settings().backend_base_url

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/actuator/health")

    async def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/tickets/{ticket_id}")

    async def add_comment(self, ticket_id: str, comment: str) -> dict[str, Any]:
        return await self._request("POST", f"/tickets/{ticket_id}/comment", json={"comment": comment})

    async def assign_ticket(self, ticket_id: str, assignee: str) -> dict[str, Any]:
        return await self._request("POST", f"/tickets/{ticket_id}/assign", json={"assignee": assignee})

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/orders/{order_id}")

    async def refund_check(self, order_id: str, reason: str) -> dict[str, Any]:
        return await self._request("POST", f"/orders/{order_id}/refund-check", json={"reason": reason})

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            response = await client.request(method, path, json=json)
            response.raise_for_status()
            return response.json()
