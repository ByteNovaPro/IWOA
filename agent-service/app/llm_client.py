from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.config import ModelSettings


class LlmClient:
    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings

    async def plan(self, user_message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        system_prompt = """
你是智能工单助手的任务规划器。你必须将用户请求解析为 JSON。

可选 intent:
- get_ticket
- add_comment
- assign_ticket
- get_order
- refund_check
- fallback

请只返回一个 JSON 对象，不要返回 Markdown，不要解释。
JSON 字段:
{
  "intent": "get_ticket | add_comment | assign_ticket | get_order | refund_check | fallback",
  "ticket_id": "T-1001 或空字符串",
  "order_id": "O-9001 或空字符串",
  "comment": "评论内容或空字符串",
  "assignee": "指派对象或空字符串",
  "reason": "退款原因或空字符串",
  "needs_human": false,
  "fallback_message": "当 intent=fallback 时给用户的回复，否则为空字符串"
}

规则:
- 如果用户要查工单，选 get_ticket
- 如果用户要追加评论，选 add_comment
- 如果用户要改负责人，选 assign_ticket
- 如果用户要查订单，选 get_order
- 如果用户要做退款校验，选 refund_check
- 如果当前消息缺少编号，但上下文里已经有最近一次提到的工单号或订单号，可以复用上下文
- 如果信息不足或意图不清楚，选 fallback
- 不要编造工单号或订单号
""".strip()
        user_prompt = json.dumps(
            {
                "user_message": user_message,
                "conversation_context": context or {},
            },
            ensure_ascii=False,
        )
        return await self._chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )

    async def answer(self, user_message: str, plan: dict[str, Any], tool_result: dict[str, Any] | None) -> str:
        system_prompt = """
你是智能工单助手。你的任务是基于工具调用结果，用简洁、专业、自然的中文回复用户。

要求:
- 不要编造工具结果中没有的数据
- 优先直接回答用户问题
- 如果是失败或兜底场景，要明确说明原因并给出下一步建议
- 控制在 2 到 4 句话内
""".strip()
        user_prompt = json.dumps(
            {
                "user_message": user_message,
                "plan": plan,
                "tool_result": tool_result,
            },
            ensure_ascii=False,
        )
        data = await self._chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )
        return data["choices"][0]["message"]["content"].strip()

    async def answer_stream(
        self,
        user_message: str,
        plan: dict[str, Any],
        tool_result: dict[str, Any] | None,
    ) -> AsyncIterator[str]:
        system_prompt = """
你是智能工单助手。你的任务是基于工具调用结果，用简洁、专业、自然的中文回复用户。

要求:
- 不要编造工具结果中没有的数据
- 优先直接回答用户问题
- 如果是失败或兜底场景，要明确说明原因并给出下一步建议
- 控制在 2 到 4 句话内
""".strip()
        user_prompt = json.dumps(
            {
                "user_message": user_message,
                "plan": plan,
                "tool_result": tool_result,
            },
            ensure_ascii=False,
        )
        async for chunk in self._chat_stream(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        ):
            yield chunk

    async def _chat_json(self, system_prompt: str, user_prompt: str, temperature: float) -> dict[str, Any]:
        data = await self._chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=temperature)
        content = data["choices"][0]["message"]["content"]
        return self._extract_json(content)

    async def _chat(self, system_prompt: str, user_prompt: str, temperature: float) -> dict[str, Any]:
        url = f"{self.settings.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def _chat_stream(self, system_prompt: str, user_prompt: str, temperature: float) -> AsyncIterator[str]:
        url = f"{self.settings.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue

                    payload = json.loads(data)
                    delta = payload["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if isinstance(content, str) and content:
                        yield content
                    elif isinstance(content, list):
                        text = "".join(
                            item.get("text", "")
                            for item in content
                            if isinstance(item, dict)
                        )
                        if text:
                            yield text

    @staticmethod
    def _extract_json(content: str) -> dict[str, Any]:
        content = content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if len(lines) >= 3:
                content = "\n".join(lines[1:-1]).strip()

        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("Model did not return JSON")
        return json.loads(content[start:end + 1])
