import json
from dataclasses import dataclass
from typing import Any, Protocol

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.provider_settings import ProviderSettings


class ChatProvider(Protocol):
    async def complete(self, messages: list[dict[str, str]]) -> str: ...


class OpenAIChatProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def complete(self, messages: list[dict[str, str]]) -> str:
        async with AsyncOpenAI(api_key=self.api_key, timeout=90) as client:
            response = await client.responses.create(model=self.model, input=messages)
        return response.output_text

    async def complete_with_tools(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        async with AsyncOpenAI(api_key=self.api_key, timeout=90) as client:
            response = await client.chat.completions.create(model=self.model, messages=messages, tools=tools, tool_choice="auto")
        return response.choices[0].message


class OpenAICompatibleProvider:
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def complete(self, messages: list[dict[str, str]]) -> str:
        async with AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=90) as client:
            response = await client.chat.completions.create(model=self.model, messages=messages)
        return response.choices[0].message.content or ""

    async def complete_with_tools(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        async with AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=90) as client:
            response = await client.chat.completions.create(model=self.model, messages=messages, tools=tools, tool_choice="auto")
        return response.choices[0].message


@dataclass
class AnthropicFunction:
    name: str
    arguments: str


@dataclass
class AnthropicToolCall:
    id: str
    function: AnthropicFunction

    def model_dump(self, *, exclude_none: bool = False) -> dict[str, Any]:
        return {"id": self.id, "type": "function", "function": {"name": self.function.name, "arguments": self.function.arguments}}


@dataclass
class AnthropicAssistantMessage:
    content: str
    tool_calls: list[AnthropicToolCall]


def _anthropic_messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    converted: list[dict[str, Any]] = []
    pending_tool_results: list[dict[str, Any]] = []

    def append(role: str, content: Any) -> None:
        if not content:
            return
        if converted and converted[-1]["role"] == role:
            previous = converted[-1]["content"]
            left = previous if isinstance(previous, list) else [{"type": "text", "text": previous}]
            right = content if isinstance(content, list) else [{"type": "text", "text": content}]
            converted[-1]["content"] = left + right
        else:
            converted.append({"role": role, "content": content})

    def flush_tool_results() -> None:
        if pending_tool_results:
            append("user", pending_tool_results.copy())
            pending_tool_results.clear()

    for item in messages:
        role = item.get("role")
        if role == "system":
            system_parts.append(str(item.get("content") or ""))
            continue
        if role == "tool":
            pending_tool_results.append({
                "type": "tool_result",
                "tool_use_id": item.get("tool_call_id", ""),
                "content": str(item.get("content") or ""),
            })
            continue
        flush_tool_results()
        tool_calls = item.get("tool_calls") or []
        if role == "assistant" and tool_calls:
            blocks: list[dict[str, Any]] = []
            content = item.get("content")
            if content:
                blocks.append({"type": "text", "text": str(content)})
            for call in tool_calls:
                function = call.get("function", {})
                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                blocks.append({"type": "tool_use", "id": call.get("id", ""), "name": function.get("name", ""), "input": arguments})
            append("assistant", blocks)
        elif role in {"user", "assistant"}:
            append(role, str(item.get("content") or ""))
    flush_tool_results()
    return "\n\n".join(part for part in system_parts if part.strip()), converted


class AnthropicChatProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def _create(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> Any:
        system, history = _anthropic_messages(messages)
        kwargs: dict[str, Any] = {"model": self.model, "max_tokens": 4096, "messages": history}
        if system:
            kwargs["system"] = system
        if tools is not None:
            kwargs["tools"] = [
                {"name": entry["function"]["name"], "description": entry["function"].get("description", ""), "input_schema": entry["function"]["parameters"]}
                for entry in tools
            ]
        async with AsyncAnthropic(api_key=self.api_key, timeout=90) as client:
            return await client.messages.create(**kwargs)

    async def complete(self, messages: list[dict[str, str]]) -> str:
        response = await self._create(messages)
        return "\n".join(str(block.text) for block in response.content if getattr(block, "type", None) == "text")

    async def complete_with_tools(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AnthropicAssistantMessage:
        response = await self._create(messages, tools)
        text = "\n".join(str(block.text) for block in response.content if getattr(block, "type", None) == "text")
        calls = [
            AnthropicToolCall(id=block.id, function=AnthropicFunction(name=block.name, arguments=json.dumps(block.input, ensure_ascii=False)))
            for block in response.content
            if getattr(block, "type", None) == "tool_use"
        ]
        return AnthropicAssistantMessage(content=text, tool_calls=calls)


def build_chat_provider(settings: ProviderSettings, api_key: str) -> ChatProvider:
    if settings.provider == "openai":
        return OpenAIChatProvider(api_key, settings.model)
    if settings.provider == "anthropic":
        return AnthropicChatProvider(api_key, settings.model)
    base_url = "https://ai.hackclub.com/proxy/v1" if settings.provider == "hackclub" else settings.hermes_base_url
    return OpenAICompatibleProvider(api_key, settings.model, base_url)
