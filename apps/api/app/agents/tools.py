import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

LOCAL_TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".log", ".xml", ".html", ".css", ".js", ".ts", ".py"}
LOCAL_FOLDERS = ("Documents", "Desktop", "Downloads")

TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "web_search", "description": "Search the web for current public information and return short results with URLs.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "read_local_file", "description": "Read a text document from the user's Documents, Desktop, or Downloads folder.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Absolute file path"}}, "required": ["path"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "write_local_file", "description": "Create or update a UTF-8 text file in the user's Documents, Desktop, or Downloads folder. Set overwrite=true only when the user asks to replace an existing file.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Absolute destination file path"}, "content": {"type": "string", "description": "Text to save"}, "overwrite": {"type": "boolean", "description": "Whether the user explicitly asked to replace an existing file"}}, "required": ["path", "content", "overwrite"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "browser_task", "description": "Open a visible local browser and perform the requested task. The user can take over the browser for login or help, then return control to Atlas to resume; the browser closes after the task completes.", "parameters": {"type": "object", "properties": {"instruction": {"type": "string", "description": "The requested browser action and desired result"}}, "required": ["instruction"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "outlook_search_mail", "description": "Search messages in the signed-in classic Outlook Inbox, Sent Items, or both. Read-only. Use only when the user requests mail review. For old-client research, use both folders and chronology=oldest; for finding current contacts, query a company/person. This action requires approval in Review mode.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Optional text to find in sender, subject, or message body."}, "unread_only": {"type": "boolean", "description": "Return only unread messages"}, "max_results": {"type": "integer", "description": "Maximum number of messages to return, from 1 to 20"}, "folder_scope": {"type": "string", "enum": ["inbox", "sent", "both"], "description": "Search Inbox, Sent Items, or both"}, "chronology": {"type": "string", "enum": ["newest", "oldest"], "description": "Choose newest or oldest matching messages"}}, "required": ["query", "unread_only", "max_results", "folder_scope", "chronology"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "outlook_send_mail", "description": "Send an email from the current classic Outlook profile. Only use when the user explicitly asks to send. A separate user approval is always required, including in Unrestricted mode; the exact recipient, subject and message body are shown for review. Never call this for a draft-only request.", "parameters": {"type": "object", "properties": {"to": {"type": "array", "items": {"type": "string", "maxLength": 320}, "minItems": 1, "maxItems": 20, "description": "One or more explicit recipient email addresses"}, "cc": {"type": "array", "items": {"type": "string", "maxLength": 320}, "maxItems": 20, "description": "Optional explicit CC email addresses"}, "subject": {"type": "string", "minLength": 1, "maxLength": 500, "description": "Exact email subject"}, "body": {"type": "string", "minLength": 1, "maxLength": 10000, "description": "Exact plain-text email body"}}, "required": ["to", "cc", "subject", "body"], "additionalProperties": False}}},
]


def is_sensitive(tool_name: str) -> bool:
    return tool_name in {"read_local_file", "write_local_file", "browser_task", "outlook_search_mail", "outlook_send_mail"}


def validate_outlook_send_args(args: dict[str, Any]) -> None:
    to, cc = args.get("to"), args.get("cc", [])
    subject, body = args.get("subject"), args.get("body")
    if not isinstance(to, list) or not isinstance(cc, list) or not 1 <= len(to) <= 20 or len(cc) > 20:
        raise ValueError("Provide 1 to 20 To recipients and at most 20 CC recipients.")
    if not all(isinstance(address, str) and re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", address.strip()) for address in to + cc):
        raise ValueError("Use explicit email addresses without display-name syntax.")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 500:
        raise ValueError("Email subject must be between 1 and 500 characters.")
    if not isinstance(body, str) or not body.strip() or len(body) > 10000:
        raise ValueError("Email body must be between 1 and 10,000 characters.")


def validate_file_path(value: str, *, must_exist: bool) -> Path:
    target = Path(value).expanduser().resolve(strict=must_exist)
    roots = [(Path.home() / name).resolve() for name in LOCAL_FOLDERS]
    if not any(target == root or root in target.parents for root in roots if root.exists()):
        raise ValueError("File access is limited to your Documents, Desktop, and Downloads folders.")
    if target.suffix.lower() not in LOCAL_TEXT_EXTENSIONS:
        raise ValueError("Only common UTF-8 text file types are supported.")
    return target


def describe_action(name: str, args: dict[str, Any]) -> str:
    path = str(args.get("path", ""))
    if name == "browser_task":
        return f"Open local browser and perform: {str(args.get('instruction', ''))[:500]}"
    if name == "outlook_search_mail":
        query = str(args.get("query", "")).strip() or "any message"
        unread = "unread " if args.get("unread_only") else ""
        folders = str(args.get("folder_scope", "both"))
        chronology = str(args.get("chronology", "newest"))
        return f"Read up to {args.get('max_results', 10)} {unread}{chronology}-ordered classic Outlook messages from {folders} matching: {query[:250]}"
    if name == "outlook_send_mail":
        to = ", ".join(str(address) for address in args.get("to", []))
        cc = ", ".join(str(address) for address in args.get("cc", []))
        return (f"SEND EMAIL FROM CLASSIC OUTLOOK\nTo: {to}\nCC: {cc or '(none)'}\n"
                f"Subject: {str(args.get('subject', ''))}\n\nExact message body:\n{str(args.get('body', ''))}")
    if name == "write_local_file":
        verb = "Replace" if args.get("overwrite") else "Create"
        return f"{verb} text file: {path}"
    if name == "read_local_file":
        return f"Read local file: {path}"
    return f"Run {name}"


async def execute_tool(name: str, args: dict[str, Any], *, task_id: str | None = None) -> str:
    if name == "web_search":
        query = str(args.get("query", "")).strip()
        if not query or len(query) > 500:
            raise ValueError("Search query must be between 1 and 500 characters.")
        if re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", query, flags=re.IGNORECASE):
            raise ValueError("Do not send private email addresses to public web search. Search by person and organization name instead.")
        from ddgs import DDGS
        results = DDGS().text(query, max_results=5)
        return json.dumps([{"title": row.get("title"), "url": row.get("href"), "snippet": row.get("body")} for row in results], ensure_ascii=False)
    if name == "read_local_file":
        target = validate_file_path(str(args.get("path", "")), must_exist=True)
        if not target.is_file() or target.stat().st_size > 2_000_000:
            raise ValueError("Choose a file up to 2 MB.")
        try:
            return target.read_text(encoding="utf-8")[:30000]
        except UnicodeDecodeError as exc:
            raise ValueError("This tool can read UTF-8 text files only.") from exc
    if name == "write_local_file":
        target = validate_file_path(str(args.get("path", "")), must_exist=False)
        if not target.parent.is_dir():
            raise ValueError("The destination folder must already exist.")
        content = args.get("content")
        if not isinstance(content, str) or len(content.encode("utf-8")) > 1_000_000:
            raise ValueError("File content must be text smaller than 1 MB.")
        if target.exists() and not args.get("overwrite", False):
            try:
                if target.is_file() and target.read_text(encoding="utf-8") == content:
                    return f"File already contains the requested content: {target}."
            except (OSError, UnicodeDecodeError):
                pass
            raise ValueError("The destination already exists. Ask the user whether to replace it.")
        if target.exists() and not target.is_file():
            raise ValueError("The destination must be a regular file.")
        if target.exists() and args.get("overwrite", False):
            try:
                if target.is_file() and target.read_text(encoding="utf-8") == content:
                    return f"File already contains the requested content: {target}."
            except (OSError, UnicodeDecodeError):
                pass
        temp_path = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", newline="", dir=target.parent, delete=False, suffix=".atlas-tmp") as handle:
                temp_path = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if target.exists() and not args.get("overwrite", False):
                raise ValueError("The destination already exists. Ask the user whether to replace it.")
            os.replace(temp_path, target)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()
        return f"Saved {len(content)} characters to {target}."
    if name == "browser_task":
        instruction = args.get("instruction")
        if not isinstance(instruction, str) or not instruction.strip() or len(instruction) > 2000:
            raise ValueError("Browser instructions must be between 1 and 2,000 characters.")
        from app.agents.browser import run_browser_task
        from app.credentials import get_secret, provider_key_name
        from app.provider_settings import get_provider_settings

        settings = get_provider_settings()
        key = get_secret(provider_key_name(settings.provider))
        if not key:
            raise ValueError("Configure the selected AI provider before using browser automation.")
        if settings.provider == "openai":
            base_url = "https://api.openai.com/v1"
        elif settings.provider == "hackclub":
            base_url = "https://ai.hackclub.com/proxy/v1"
        elif settings.provider == "hermes":
            base_url = settings.hermes_base_url
        else:
            base_url = None
        if not task_id:
            raise RuntimeError("Browser task context is missing.")
        return await run_browser_task(instruction.strip(), task_id=task_id, model=settings.model, api_key=key, provider=settings.provider, base_url=base_url)
    if name == "outlook_search_mail":
        query = args.get("query", "")
        unread_only = args.get("unread_only", False)
        max_results = args.get("max_results", 10)
        folder_scope = args.get("folder_scope", "both")
        chronology = args.get("chronology", "newest")
        if not isinstance(query, str) or not isinstance(unread_only, bool) or not isinstance(max_results, int) or not isinstance(folder_scope, str) or not isinstance(chronology, str):
            raise ValueError("Invalid Outlook search options.")
        from app.integrations.outlook import search_outlook_mail
        return await search_outlook_mail(query, unread_only=unread_only, max_results=max_results, folder_scope=folder_scope, chronology=chronology)
    if name == "outlook_send_mail":
        validate_outlook_send_args(args)
        to, cc, subject, body = args["to"], args.get("cc", []), args["subject"], args["body"]
        from app.integrations.outlook import send_outlook_mail
        return await send_outlook_mail(to, cc, subject, body)
    raise ValueError(f"Unknown tool: {name}")
