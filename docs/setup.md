# Setup on Windows

1. Install Node.js 22 or newer and Python 3.12.
2. From the project root, run `./start.ps1` in PowerShell. First launch creates a virtual environment and installs dependencies.
3. Open `http://127.0.0.1:3000`.
4. Run `./stop.ps1` to stop both services. Runtime logs and PID files are kept under `work/runtime`.

## Connect a provider

Open Settings in Atlas and select a provider. The default is the Hack Club AI proxy and `openai/gpt-4o-mini`; direct OpenAI, Anthropic Claude, and a local Hermes-compatible server are also supported. Paste the selected provider's key and save. Atlas stores each provider key separately in Windows Credential Manager. Hermes can be selected when its API server is already running locally at `http://127.0.0.1:8642/v1`.

Send a message from Overview. The conversation stays in the current tab and resets when reloaded. Each request sends its message history to the selected AI endpoint.

## Outlook

Outlook mail tools use the classic Outlook desktop profile configured for the signed-in Windows account. Install classic Outlook and finish its normal account setup. In Review mode, approve each mail-reading task. Any send action displays the exact recipients, subject, and body and always requires approval, including in Unrestricted mode. The connector does not support new Outlook, attachments, drafts, or delete/edit actions.

The local SQLite database is stored at `apps/api/atlas.db`. Back it up by stopping Atlas and copying that file.

## Recurring jobs

Create hourly, daily, or weekly interval jobs, or choose Cron schedule to enter a five-field cron expression (minute, hour, day, month, weekday) and IANA timezone. For example, `0 8 * * 1-5` runs every weekday at 8:00 AM in the selected timezone. Scheduled tasks run locally while Atlas is running. Existing interval jobs are preserved when Atlas updates its SQLite schema.
