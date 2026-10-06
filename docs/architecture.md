# Architecture

Atlas runs directly on Windows without Docker. Next.js serves the dashboard at 127.0.0.1:3000; FastAPI serves the API at 127.0.0.1:8000; SQLite stores conversations, tasks, memories, approvals, tool executions, and audit events in apps/api/atlas.db. The Next.js server proxies /api/* to FastAPI.

## Agent and tools

Tasks use a LangGraph workflow and a provider adapter. OpenAI Responses, the native Anthropic Messages API, the Hack Club chat completions proxy, and a loopback Hermes API server are supported. Tool-enabled task turns use provider-specific tool formats behind a shared adapter. The registered tools include web_search, local file tools, browser_task, and classic Outlook mail tools.

Web search uses DDGS and returns public search snippets and source URLs. Private email addresses are rejected from public search queries. Local file actions are limited to UTF-8 text formats in the user's Documents, Desktop, and Downloads folders. Writes use a temporary file and an atomic replacement. File, browser, and Outlook actions consult the saved review/unrestricted policy and are recorded in SQLite. Browser automation uses Browser Use and launches Chrome or Edge discovered on the current Windows installation, with an isolated Atlas profile; each session closes after the task. Outlook mail access uses the signed-in classic Outlook profile through Windows COM. Reads use the normal permission mode; every send has a non-bypassable per-message approval.

## Recurring tasks

Scheduled jobs are stored in SQLite and polled by a small in-process async worker while the local API is running. The worker advances a job's next-run time and creates its task in the same database transaction, then hands the task to LangGraph. Missed jobs are run once after Atlas restarts; the worker does not create a burst of missed occurrences.

## Data and trust boundaries

Provider API keys are stored in Windows Credential Manager. Provider and permission preferences are stored locally. Task records and tool results persist in SQLite. The server binds only to loopback and currently has no authentication; keep it on this machine.

Cloud provider requests contain the task prompt plus any retrieved file contents, browser page data, and tool results needed to answer it. Search queries leave the PC to public search services. Treat returned web pages and file contents as untrusted reference data.

## Remaining platform work

Gmail and calendar integrations, general cross-app desktop control, semantic memory retrieval, multi-agent delegation, and authenticated access are not implemented yet. New Outlook is not supported by the current local mail connector.
