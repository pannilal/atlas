# BaysysTech Atlas

Atlas is a local-first AI assistant workspace for Windows. The dashboard, FastAPI service, SQLite database, task history, memories, approvals, and audit records stay on this PC. AI requests use the provider you configure. Docker is not required.

## Start Atlas

Prerequisites: Windows 10/11, Node.js 22 or newer, and Python 3.12. Run `./start.ps1` in PowerShell. On first launch it creates a Python virtual environment and installs API dependencies; web dependencies are installed if needed. Services bind to `127.0.0.1` and the dashboard opens at http://127.0.0.1:3000.

API health: http://127.0.0.1:8000/api/v1/health. API docs: http://127.0.0.1:8000/docs. Stop services with `./stop.ps1`. Logs and process IDs are under `work/runtime`; SQLite data is in `apps/api/atlas.db`.

## Configure AI

Open Settings in the dashboard. Hack Club is selected by default (`openai/gpt-4o-mini`). OpenAI, Anthropic Claude, and a local Hermes API server are also supported. Save the API key in Settings; Windows Credential Manager stores it and Atlas never returns it to the web UI.

## Current capabilities

- Chat with the configured AI provider and keep conversations in the local database.
- Submit background tasks and inspect their state, events, and results.
- Search the public web using the agent's web-search tool.
- Read, create, and replace common text files under Documents, Desktop, and Downloads.
- Open a visible local Chrome or Edge window for requested browser tasks; Atlas uses an isolated Atlas profile and closes it after each task.
- Search Inbox and Sent Items in the current Windows user's classic Outlook profile. Every send requires exact-message approval, including in Unrestricted mode; delete and edit actions are not supported.
- Run browser actions in Review mode after per-task approval, or skip that prompt in acknowledged Unrestricted mode.
- Use Review mode to approve each local file action, or acknowledge the risks and enable Unrestricted mode to skip those prompts.
- Manage saved memories, inspect approvals, and review audit events through the API.
- Schedule recurring tasks at hourly, daily, or weekly intervals, or use five-field cron expressions with an IANA timezone (for example, weekdays at 8 AM); jobs run while Atlas is running on this PC.

Unrestricted mode only affects supported Atlas tools. It does not bypass Windows security or give Atlas capabilities it does not have. The app does not execute files. Prompts, email content, browser page data, and file contents used for a task may be sent to the selected AI provider. Email sends still require a separate per-message approval. See `docs/security.md` before changing the permission mode.

## In progress

Gmail and calendar integrations, general desktop control, semantic memory retrieval, and multi-agent delegation remain to be built. Outlook supports bounded Inbox/Sent Items search and sends only after exact-message approval through the classic Outlook desktop profile; new Outlook is not supported by this connector. Atlas has no authentication yet and must stay bound to loopback.

See `docs/architecture.md` and `docs/setup.md` for implementation and setup details.
