# Security notes

Atlas binds its web and API services to 127.0.0.1. It has no sign-in or authorization layer, so do not expose it to a LAN or the public internet. API keys are held in Windows Credential Manager. Provider selection is stored in a local ignored settings file.

Chat prompts and tool results are sent to the selected AI provider. Web searches go to public search services. Local file content read by Atlas and browser page data needed for a browser task may also be included in AI requests.

Automatic task-memory extraction is off by default. If enabled in Settings, each completed task's instruction and result are sent to the selected AI provider for extraction of up to three durable notes; those notes are stored locally and can be reviewed or deleted on the Memory page.

## Tool permissions

Review mode is the default. Web search is read-only and runs without an approval prompt. Reading, creating, or replacing files in Documents, Desktop, or Downloads requires a per-action approval. Browser tasks require approval before opening the visible local browser. Outlook mail search requires approval before reading message content. Sending an Outlook message always requires a separate approval, regardless of permission mode; that approval displays the exact To, CC, subject, and body. Approval applies only to the matching message arguments. Approvals show the operation and are recorded with the task and audit log.

Unrestricted mode skips Atlas approval prompts for supported sensitive actions. At present, that includes reading and writing common UTF-8 text formats (txt, md, csv, json, yaml, log, xml, html, css, js, ts, and py) under Documents, Desktop, or Downloads; browser automation that can navigate and interact with websites; and bounded Inbox/Sent Items search in classic Outlook. Mail, page, and file content may be sent to the configured AI provider. Writes are bounded to 1 MB; file reads to 2 MB; Outlook search returns at most 20 messages with short body previews. Sending a message is never covered by Unrestricted mode: every send requires its own approval displaying the exact recipients, subject, and body. The app does not delete or edit mail, execute files, or bypass Windows permissions.

All tool paths are resolved before access so paths that escape the allowed folders are rejected. Destinations must use an allowed text extension and an existing parent folder. Replacing a file requires the model to set overwrite=true; the approval request includes the exact path and operation.

Unrestricted mode is not a Windows sandbox. Keep it off when Atlas should ask before each supported file action. The policy only governs tools registered by Atlas and does not grant missing capabilities.

## Credentials

The AI API key was shared in the setup conversation. Rotate it if it should no longer remain valid in chat history.
