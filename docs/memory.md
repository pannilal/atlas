# Memory and retention

Atlas keeps conversation transcripts as short-term context, stores user-managed semantic facts and preferences, and supports episodic notes for past events. Memories remain in the local SQLite database and can be searched or deleted from the Memory page.

Automatic extraction from completed tasks is off by default. When enabled in Settings, Atlas sends the task instruction and result to the selected AI provider and asks it to retain up to three durable facts or preferences. It is instructed to skip task-specific summaries, secrets, credentials, contact details, and sensitive personal information; obvious email addresses, phone numbers, and common API-key patterns are filtered before storage. Extraction errors do not fail the task. Users can review and delete extracted notes on the Memory page.

Memory lookup ranks saved notes with a local lexical relevance score based on query-term frequency and rarity, then uses exact phrase matches and recency as ranking signals. Memory contents are supplied to the model as reference data, never as instructions. Atlas does not currently calculate vector embeddings.
