from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx

from app.backend_client import BackendClient
from app.config import load_settings
from app.llm_client import LlmClient


@dataclass
class ConversationState:
    last_ticket_id: str = ""
    last_order_id: str = ""
    pending_intent: str = ""
    pending_field: str = ""
    pending_payload: dict[str, str] = field(default_factory=dict)


class AgentWorkflow:
    def __init__(self, backend_client: BackendClient | None = None) -> None:
        self.backend_client = backend_client or BackendClient()
        self.settings = load_settings()
        self.llm_client = LlmClient(self.settings) if self.settings.is_configured else None
        self.conversations: dict[str, ConversationState] = {}

    async def run(self, message: str, user_id: str = "demo-user") -> tuple[str, str, list[dict[str, Any]]]:
        try:
            prepared = await self._prepare(message, user_id)
            if prepared["intent"] == "fallback":
                return self._fallback("fallback", prepared["answer"])

            answer = await self._generate_answer(
                prepared["message"],
                prepared["plan"],
                prepared["tool_result"],
            )
            return prepared["intent"], answer, prepared["tool_calls"]
        except httpx.HTTPStatusError as exc:
            return self._handle_http_status_error(exc)
        except httpx.HTTPError:
            return self._handle_http_error()
        except ValueError:
            return await self._run_rule_based(message.strip(), user_id)

    async def stream(self, message: str, user_id: str = "demo-user") -> AsyncIterator[dict[str, Any]]:
        try:
            prepared = await self._prepare(message, user_id)
            yield {
                "type": "meta",
                "intent": prepared["intent"],
                "tool_calls": prepared["tool_calls"],
            }

            if prepared["intent"] == "fallback":
                async for chunk in self._stream_text(prepared["answer"]):
                    yield {"type": "delta", "delta": chunk}
                yield {
                    "type": "done",
                    "intent": "fallback",
                    "tool_calls": [],
                    "answer": prepared["answer"],
                }
                return

            if self.llm_client:
                chunks: list[str] = []
                async for chunk in self.llm_client.answer_stream(
                    prepared["message"],
                    prepared["plan"],
                    prepared["tool_result"],
                ):
                    chunks.append(chunk)
                    yield {"type": "delta", "delta": chunk}

                answer = "".join(chunks).strip()
                if not answer:
                    answer = self._format_rule_answer(prepared["plan"], prepared["tool_result"])
            else:
                answer = self._format_rule_answer(prepared["plan"], prepared["tool_result"])
                async for chunk in self._stream_text(answer):
                    yield {"type": "delta", "delta": chunk}

            yield {
                "type": "done",
                "intent": prepared["intent"],
                "tool_calls": prepared["tool_calls"],
                "answer": answer,
            }
        except httpx.HTTPStatusError as exc:
            answer = self._handle_http_status_error(exc)[1]
            async for chunk in self._stream_text(answer):
                yield {"type": "delta", "delta": chunk}
            yield {"type": "done", "intent": "fallback", "tool_calls": [], "answer": answer}
        except httpx.HTTPError:
            answer = self._handle_http_error()[1]
            async for chunk in self._stream_text(answer):
                yield {"type": "delta", "delta": chunk}
            yield {"type": "done", "intent": "fallback", "tool_calls": [], "answer": answer}
        except ValueError:
            intent, answer, tool_calls = await self._run_rule_based(message.strip(), user_id)
            async for chunk in self._stream_text(answer):
                yield {"type": "delta", "delta": chunk}
            yield {"type": "done", "intent": intent, "tool_calls": tool_calls, "answer": answer}

    async def _prepare(self, message: str, user_id: str) -> dict[str, Any]:
        normalized = message.strip()
        state = self._get_state(user_id)
        plan = await self._create_plan(normalized, state)
        intent = plan["intent"]
        tool_calls: list[dict[str, Any]] = []

        if intent == "fallback":
            self._update_state_from_plan(state, plan, success=False)
            return {
                "message": normalized,
                "intent": "fallback",
                "plan": plan,
                "tool_calls": [],
                "tool_result": None,
                "answer": plan.get("fallback_message") or "请补充工单号、订单号或具体操作。",
            }

        tool_result = await self._execute_plan(plan, tool_calls)
        self._update_state_from_plan(state, plan, success=True)
        return {
            "message": normalized,
            "intent": intent,
            "plan": plan,
            "tool_calls": tool_calls,
            "tool_result": tool_result,
            "answer": "",
        }

    async def _create_plan(self, message: str, state: ConversationState) -> dict[str, Any]:
        rule_plan = self._rule_based_plan(message, state)
        if rule_plan["intent"] != "fallback" or not self.llm_client:
            return rule_plan

        llm_plan = await self.llm_client.plan(message, self._conversation_context(state))
        return self._merge_with_context(llm_plan, state)

    async def _execute_plan(self, plan: dict[str, Any], tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
        intent = plan["intent"]
        if intent == "get_ticket":
            ticket_id = plan["ticket_id"]
            tool_calls.append({"tool": "GET /tickets/{id}", "ticket_id": ticket_id})
            return await self.backend_client.get_ticket(ticket_id)

        if intent == "add_comment":
            ticket_id = plan["ticket_id"]
            comment = plan["comment"]
            if not ticket_id or not comment:
                raise ValueError("missing add_comment fields")
            tool_calls.append({"tool": "POST /tickets/{id}/comment", "ticket_id": ticket_id})
            return await self.backend_client.add_comment(ticket_id, comment)

        if intent == "assign_ticket":
            ticket_id = plan["ticket_id"]
            assignee = plan["assignee"]
            if not ticket_id or not assignee:
                raise ValueError("missing assign_ticket fields")
            tool_calls.append({"tool": "POST /tickets/{id}/assign", "ticket_id": ticket_id})
            return await self.backend_client.assign_ticket(ticket_id, assignee)

        if intent == "get_order":
            order_id = plan["order_id"]
            tool_calls.append({"tool": "GET /orders/{id}", "order_id": order_id})
            return await self.backend_client.get_order(order_id)

        if intent == "refund_check":
            order_id = plan["order_id"]
            reason = plan["reason"] or "用户发起退款申请"
            if not order_id:
                raise ValueError("missing refund_check fields")
            tool_calls.append({"tool": "POST /orders/{id}/refund-check", "order_id": order_id})
            return await self.backend_client.refund_check(order_id, reason)

        raise ValueError("unsupported intent")

    async def _generate_answer(self, message: str, plan: dict[str, Any], tool_result: dict[str, Any]) -> str:
        if self.llm_client:
            return await self.llm_client.answer(message, plan, tool_result)
        return self._format_rule_answer(plan, tool_result)

    @staticmethod
    async def _stream_text(text: str, chunk_size: int = 12) -> AsyncIterator[str]:
        for index in range(0, len(text), chunk_size):
            yield text[index:index + chunk_size]
            await asyncio.sleep(0)

    async def _run_rule_based(self, normalized: str, user_id: str) -> tuple[str, str, list[dict[str, Any]]]:
        state = self._get_state(user_id)
        plan = self._rule_based_plan(normalized, state)
        if plan["intent"] == "fallback":
            self._update_state_from_plan(state, plan, success=False)
            return self._fallback("fallback", plan["fallback_message"])
        tool_calls: list[dict[str, Any]] = []
        try:
            tool_result = await self._execute_plan(plan, tool_calls)
            self._update_state_from_plan(state, plan, success=True)
            answer = self._format_rule_answer(plan, tool_result)
            return plan["intent"], answer, tool_calls
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return self._fallback("fallback", "我调用后端时没有找到对应的工单或订单，请确认编号是否正确。")
            return self._fallback("fallback", f"后端接口调用失败，状态码 {exc.response.status_code}，建议转人工处理。")
        except httpx.HTTPError:
            return self._fallback("fallback", "当前无法连接业务后端，建议先检查 Java 服务是否已启动。")

    def _rule_based_plan(self, message: str, state: ConversationState) -> dict[str, Any]:
        if pending_plan := self._resolve_pending_follow_up(message, state):
            return pending_plan

        ticket_id = self._extract_id(message, r"T-\d+") or self._infer_ticket_id_from_context(message, state)
        order_id = self._extract_id(message, r"O-\d+") or self._infer_order_id_from_context(message, state)

        if self._looks_like_comment(message):
            comment = self._extract_comment(message)
            if ticket_id and comment:
                return self._plan_template("add_comment", ticket_id=ticket_id, comment=comment)
            if ticket_id:
                return self._plan_template(
                    "fallback",
                    fallback_message=f"我知道你想给工单 {ticket_id} 添加评论了，请把评论内容直接发给我。",
                    pending_intent="add_comment",
                    pending_field="comment",
                    ticket_id=ticket_id,
                )
            return self._plan_template(
                "fallback",
                fallback_message="可以添加评论，但还缺工单号。请补充类似 T-1001 的工单号。",
                pending_intent="add_comment",
                pending_field="ticket_id",
                pending_payload={"comment": comment} if comment else {},
            )

        if self._looks_like_assign(message):
            assignee = self._extract_assignee(message)
            if ticket_id and assignee:
                return self._plan_template("assign_ticket", ticket_id=ticket_id, assignee=assignee)
            if ticket_id:
                return self._plan_template(
                    "fallback",
                    fallback_message=f"我知道你想调整工单 {ticket_id} 的负责人了，请告诉我要指派给谁。",
                    pending_intent="assign_ticket",
                    pending_field="assignee",
                    ticket_id=ticket_id,
                )
            return self._plan_template(
                "fallback",
                fallback_message="可以帮你改负责人，但还缺工单号。请补充类似 T-1001 的工单号。",
                pending_intent="assign_ticket",
                pending_field="ticket_id",
                pending_payload={"assignee": assignee} if assignee else {},
            )

        if ticket_id:
            return self._plan_template("get_ticket", ticket_id=ticket_id)

        if self._looks_like_refund(message):
            reason = self._extract_refund_reason(message)
            if order_id:
                return self._plan_template("refund_check", order_id=order_id, reason=reason)
            return self._plan_template(
                "fallback",
                fallback_message="可以帮你检查退款资格，但还缺订单号。请补充类似 O-9001 的订单号。",
                pending_intent="refund_check",
                pending_field="order_id",
                pending_payload={"reason": reason},
            )

        if order_id:
            return self._plan_template("get_order", order_id=order_id)

        return self._plan_template(
            "fallback",
            fallback_message="我能查工单、加评论、改负责人、查订单和检查退款资格。你可以直接说：给 T-1001 添加评论：客户已补充付款截图。",
        )

    @staticmethod
    def _plan_template(intent: str, **kwargs: Any) -> dict[str, Any]:
        plan = {
            "intent": intent,
            "ticket_id": "",
            "order_id": "",
            "comment": "",
            "assignee": "",
            "reason": "",
            "needs_human": False,
            "fallback_message": "",
            "pending_intent": "",
            "pending_field": "",
            "pending_payload": {},
        }
        plan.update(kwargs)
        return plan

    @staticmethod
    def _format_rule_answer(plan: dict[str, Any], tool_result: dict[str, Any]) -> str:
        intent = plan["intent"]
        if intent == "get_ticket":
            return (
                f"工单 {tool_result['id']} 当前状态是 {tool_result['status']}，优先级 {tool_result['priority']}，"
                f"负责人是 {tool_result['assignee']}。问题摘要：{tool_result['summary']}"
            )
        if intent == "add_comment":
            return f"工单 {tool_result['id']} 已添加评论，当前负责人是 {tool_result['assignee']}，最新评论数为 {len(tool_result['comments'])}。"
        if intent == "assign_ticket":
            return f"工单 {tool_result['id']} 已指派给 {tool_result['assignee']}，当前状态为 {tool_result['status']}。"
        if intent == "get_order":
            return f"订单 {tool_result['id']} 状态是 {tool_result['status']}，金额 {tool_result['amount']}，客户是 {tool_result['customerName']}。"
        if intent == "refund_check":
            return (
                f"订单 {tool_result['orderId']} 退款校验结果："
                f"{'可以自动退款' if tool_result['eligible'] else '不能自动退款'}。{tool_result['message']}"
            )
        return "我暂时无法准确判断你的意图，请补充更多信息。"

    @staticmethod
    def _handle_http_status_error(exc: httpx.HTTPStatusError) -> tuple[str, str, list[dict[str, Any]]]:
        if exc.response.status_code == 404:
            return AgentWorkflow._fallback("fallback", "我调用后端时没有找到对应的工单或订单，请确认编号是否正确。")
        return AgentWorkflow._fallback("fallback", f"后端接口调用失败，状态码 {exc.response.status_code}，建议转人工处理。")

    def _handle_http_error(self) -> tuple[str, str, list[dict[str, Any]]]:
        if self.llm_client:
            return self._fallback("fallback", "当前无法连接大模型服务或业务后端，请检查 Agent 配置、网络和 Java 服务。")
        return self._fallback("fallback", "当前无法连接业务后端，建议先检查 Java 服务是否已启动。")

    @staticmethod
    def _extract_id(message: str, pattern: str) -> str | None:
        match = re.search(pattern, message.upper())
        return match.group(0) if match else None

    @staticmethod
    def _extract_text_after_marker(message: str, marker: str) -> str:
        if "：" in message:
            return message.split("：", 1)[1].strip()
        if ":" in message:
            return message.split(":", 1)[1].strip()
        parts = message.split(marker, 1)
        return parts[1].strip() if len(parts) > 1 else ""

    @staticmethod
    def _extract_assignee(message: str) -> str | None:
        match = re.search(r"(给|assign to|指派给|转给)\s*([A-Za-z0-9_\-\u4e00-\u9fa5]+)", message, re.IGNORECASE)
        return match.group(2) if match else None

    @staticmethod
    def _extract_refund_reason(message: str) -> str:
        for separator in ("因为", "原因是", "原因：", "原因:"):
            if separator in message:
                return message.split(separator, 1)[1].strip()
        return "用户发起退款申请"

    def _get_state(self, user_id: str) -> ConversationState:
        if user_id not in self.conversations:
            self.conversations[user_id] = ConversationState()
        return self.conversations[user_id]

    @staticmethod
    def _conversation_context(state: ConversationState) -> dict[str, Any]:
        return {
            "last_ticket_id": state.last_ticket_id,
            "last_order_id": state.last_order_id,
            "pending_intent": state.pending_intent,
            "pending_field": state.pending_field,
            "pending_payload": state.pending_payload,
        }

    def _merge_with_context(self, plan: dict[str, Any], state: ConversationState) -> dict[str, Any]:
        merged = self._plan_template(plan.get("intent", "fallback"))
        merged.update(plan)

        if merged["intent"] in {"get_ticket", "add_comment", "assign_ticket"} and not merged["ticket_id"]:
            merged["ticket_id"] = state.last_ticket_id
        if merged["intent"] in {"get_order", "refund_check"} and not merged["order_id"]:
            merged["order_id"] = state.last_order_id
        if merged["intent"] == "fallback" and not merged["fallback_message"]:
            merged["fallback_message"] = "请补充工单号、订单号或具体操作。"
        return merged

    def _update_state_from_plan(self, state: ConversationState, plan: dict[str, Any], success: bool) -> None:
        if plan.get("ticket_id"):
            state.last_ticket_id = plan["ticket_id"]
        if plan.get("order_id"):
            state.last_order_id = plan["order_id"]

        if success:
            state.pending_intent = ""
            state.pending_field = ""
            state.pending_payload = {}
            return

        state.pending_intent = plan.get("pending_intent", "")
        state.pending_field = plan.get("pending_field", "")
        state.pending_payload = dict(plan.get("pending_payload", {}))

    def _resolve_pending_follow_up(self, message: str, state: ConversationState) -> dict[str, Any] | None:
        if not state.pending_intent or not state.pending_field:
            return None

        if state.pending_intent == "add_comment":
            if state.pending_field == "ticket_id":
                ticket_id = self._extract_id(message, r"T-\d+")
                comment = state.pending_payload.get("comment", "")
                if ticket_id and comment:
                    return self._plan_template("add_comment", ticket_id=ticket_id, comment=comment)
                if ticket_id:
                    return self._plan_template(
                        "fallback",
                        fallback_message=f"工单号收到了，是 {ticket_id}。现在把评论内容发给我就行。",
                        pending_intent="add_comment",
                        pending_field="comment",
                        ticket_id=ticket_id,
                    )
            if state.pending_field == "comment" and state.last_ticket_id:
                comment = self._extract_comment(message)
                if comment:
                    return self._plan_template("add_comment", ticket_id=state.last_ticket_id, comment=comment)

        if state.pending_intent == "assign_ticket":
            if state.pending_field == "ticket_id":
                ticket_id = self._extract_id(message, r"T-\d+")
                assignee = state.pending_payload.get("assignee", "")
                if ticket_id and assignee:
                    return self._plan_template("assign_ticket", ticket_id=ticket_id, assignee=assignee)
                if ticket_id:
                    return self._plan_template(
                        "fallback",
                        fallback_message=f"工单号收到了，是 {ticket_id}。现在告诉我要指派给谁。",
                        pending_intent="assign_ticket",
                        pending_field="assignee",
                        ticket_id=ticket_id,
                    )
            if state.pending_field == "assignee" and state.last_ticket_id:
                assignee = self._extract_assignee(message) or message.strip("：: ").strip()
                if assignee:
                    return self._plan_template("assign_ticket", ticket_id=state.last_ticket_id, assignee=assignee)

        if state.pending_intent == "refund_check" and state.pending_field == "order_id":
            order_id = self._extract_id(message, r"O-\d+")
            if order_id:
                return self._plan_template(
                    "refund_check",
                    order_id=order_id,
                    reason=state.pending_payload.get("reason", "用户发起退款申请"),
                )

        return None

    @staticmethod
    def _looks_like_comment(message: str) -> bool:
        lowered = message.lower()
        return any(keyword in message for keyword in ("评论", "备注", "留言")) or "comment" in lowered

    @staticmethod
    def _looks_like_assign(message: str) -> bool:
        lowered = message.lower()
        return any(keyword in message for keyword in ("指派", "负责人", "转给")) or "assign" in lowered

    @staticmethod
    def _looks_like_refund(message: str) -> bool:
        return "退款" in message or "refund" in message.lower()

    def _infer_ticket_id_from_context(self, message: str, state: ConversationState) -> str | None:
        if state.last_ticket_id and any(keyword in message for keyword in ("这个工单", "该工单", "继续", "再", "追加")):
            return state.last_ticket_id
        return None

    def _infer_order_id_from_context(self, message: str, state: ConversationState) -> str | None:
        if state.last_order_id and any(keyword in message for keyword in ("这个订单", "该订单", "继续", "再")):
            return state.last_order_id
        return None

    def _extract_comment(self, message: str) -> str:
        for marker in ("评论", "备注", "留言"):
            if marker in message:
                comment = self._extract_text_after_marker(message, marker)
                if comment and comment not in {"一下", "一条", "添加", "添加一条", "追加"}:
                    return comment.strip("“”\" ")
        if "：" in message or ":" in message:
            tail = self._extract_text_after_marker(message, ":")
            if tail:
                return tail.strip("“”\" ")
        return ""

    @staticmethod
    def _fallback(intent: str, answer: str) -> tuple[str, str, list[dict[str, Any]]]:
        return intent, answer, []
