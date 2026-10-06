"use client";

import Link from "next/link";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

type Message = { role: "user" | "assistant"; content: string };
type ConversationSummary = { id: string; title: string; updated_at: string };

export default function Home() {
  const [configured, setConfigured] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/v1/settings/provider").then((r) => r.json()).then((d) => setConfigured(Boolean(d.configured))).catch(() => setConfigured(false));
    void refreshConversations(true);
  }, []);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const content = draft.trim();
    if (!content || busy) return;
    setError("");
    if (!configured) { setError("Connect an AI provider in Settings to start chatting."); return; }
    const next: Message[] = [...messages, { role: "user", content }];
    setMessages(next); setDraft(""); setBusy(true);
    try {
      const response = await fetch("/api/v1/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages: next.slice(-30), conversation_id: conversationId }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Chat request failed.");
      setMessages([...next, { role: "assistant", content: data.reply }]);
      setConversationId(data.conversation_id);
      void refreshConversations(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not reach Atlas. Check that both local services are running."); }
    finally { setBusy(false); }
  }

  function onComposerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); }
  }

  function newChat() { setConversationId(null); setMessages([]); setDraft(""); setError(""); setShowHistory(false); }

  async function refreshConversations(openLatest: boolean) {
    try {
      const response = await fetch("/api/v1/conversations");
      if (!response.ok) return;
      const rows: ConversationSummary[] = await response.json();
      setConversations(rows);
      if (openLatest && rows.length) await openConversation(rows[0].id);
    } catch { /* Keep the local chat usable if conversation history is unavailable. */ }
  }

  async function openConversation(id: string) {
    if (busy) return;
    setError("");
    try {
      const response = await fetch(`/api/v1/conversations/${id}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not load this conversation.");
      setConversationId(id);
      setMessages((data.messages ?? []).map((message: Message) => ({ role: message.role, content: message.content })));
      setDraft("");
      setShowHistory(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load this conversation."); }
  }

  async function deleteConversation(id: string, title: string) {
    if (!window.confirm(`Delete “${title}” and its saved messages? This cannot be undone.`)) return;
    try {
      const response = await fetch(`/api/v1/conversations/${id}`, { method: "DELETE" });
      if (!response.ok) { const data = await response.json(); throw new Error(data.detail ?? "Could not delete this conversation."); }
      if (conversationId === id) { setConversationId(null); setMessages([]); setDraft(""); }
      await refreshConversations(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not delete this conversation."); }
  }

  return <main className={`shell overview ${showHistory ? "showHistory" : ""}`}><aside className="sidebar"><Link className="brand" href="/"><span className="brandName">BAYSYSTECH<small>ATLAS</small></span></Link><nav><Link className="active" href="/">⌂　Overview</Link><Link href="/tasks">◷　Tasks</Link><Link href="/approvals">✓　Approvals</Link><Link href="/memory">▤　Memory</Link><Link href="/audit">≡　Audit</Link><Link href="/schedules">⟳　Schedules</Link><Link href="/settings">⚙　Settings</Link></nav><div className="conversationHistory"><div className="historyHeading">RECENT CHATS</div>{conversations.length ? conversations.map((conversation) => <div key={conversation.id} className={`conversationRow ${conversationId === conversation.id ? "selected" : ""}`}><button className="conversationLink" title={conversation.title} onClick={() => void openConversation(conversation.id)} disabled={busy}>{conversation.title}</button><button className="deleteChat" title={`Delete ${conversation.title}`} aria-label={`Delete chat ${conversation.title}`} onClick={() => void deleteConversation(conversation.id, conversation.title)} disabled={busy}>×</button></div>) : <div className="historyEmpty">Your chats will appear here.</div>}</div></aside><section className="content"><header><span></span><button className="historyToggle" onClick={() => setShowHistory((shown) => !shown)} aria-expanded={showHistory}>Chats</button><button className="newChat" onClick={newChat}>＋ New chat</button></header><div className="welcome"><div className="eyebrow"></div>{messages.length === 0 ? <><h1>Good morning.</h1><p>What would you like Atlas to take care of?</p><div className="suggestions"><button onClick={() => setDraft("Help me plan my day")}>Help me plan my day <span>↗</span></button><button onClick={() => setDraft("Summarize a document for me")}>Summarize a document <span>↗</span></button></div></> : <div className="conversation" aria-live="polite">{messages.map((message, index) => <div className={`message ${message.role}`} key={`${index}-${message.role}`}><div className="messageLabel">{message.role === "user" ? "YOU" : "ATLAS"}</div><div className="messageText">{message.content}</div></div>)}{busy && <div className="message assistant"><div className="messageLabel">ATLAS</div><div className="typing"><i /><i /><i /></div></div>}<div ref={bottom} /></div>}
    <form className="composer" onSubmit={send}><textarea aria-label="Message Atlas" placeholder="Ask Atlas to research, organize, or prepare something…" value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={onComposerKey} disabled={busy} /><div className="composerBottom">{error ? <span className="chatError">{error}</span> : <span>{configured ? "Enter to send · Shift + Enter for a new line" : <>Connect your AI provider in <Link href="/settings">Settings</Link> to get started</>}</span>}<button type="submit" disabled={busy || !draft.trim()} aria-label="Send message">{busy ? "…" : "↑"}</button></div></form></div><footer></footer></section></main>;
}
