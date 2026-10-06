# Integrations

## Microsoft Outlook (classic)

Atlas accesses the current Windows user's classic Outlook profile through the local Outlook COM automation interface. No mailbox password or OAuth token is collected by Atlas. The Outlook client must be installed and have a signed-in mail profile. New Outlook is not supported by this connector.

The read tool searches Inbox, Sent Items, or both. It can return at most 20 messages per request, with sender, subject, date, unread state, and a short body preview. For historical client research, Atlas can start from older messages in both folders, extract organization and contact names, and use public web search (including public LinkedIn results) to look for current business status and professional affiliation. Public search queries must not include private email addresses. Findings should cite source URLs and distinguish verified facts from uncertainty; Atlas does not seek personal whereabouts.

Reading mail requires task approval in Review mode. Matching email bodies are sent to the configured AI provider so Atlas can analyze them. The Outlook tools do not change, delete, flag, or move messages.

The send tool accepts explicit To/CC addresses, a subject, and a plain-text body. Atlas must only call it when the user explicitly requests sending, and must show those exact fields in a per-message approval. The approval is mandatory even in Unrestricted mode; it applies only to the exact tool arguments approved. Outlook sends through the default profile after approval. Atlas reports that Outlook accepted the send call, not that a recipient received or read the message. Atlas does not support drafts, attachments, or message modification yet.
