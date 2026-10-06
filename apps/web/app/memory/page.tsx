"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type Memory = { id: string; content: string; category: "semantic" | "episodic"; updated_at: string };

export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [content, setContent] = useState("");
  const [category, setCategory] = useState<"semantic" | "episodic">("semantic");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  async function refresh(search = query) { try { const response = await fetch(`/api/v1/memory?q=${encodeURIComponent(search)}`); if (!response.ok) throw new Error(); setMemories(await response.json()); } catch { setError("Atlas API is unavailable."); } }
  useEffect(() => { void refresh(""); }, []);
  async function add(event: FormEvent) { event.preventDefault(); if (!content.trim()) return; const response = await fetch("/api/v1/memory", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content, category }) }); const data = await response.json(); if (!response.ok) { setError(data.detail ?? "Could not save memory."); return; } setContent(""); setError(""); await refresh(""); }
  async function remove(id: string) { await fetch(`/api/v1/memory/${id}`, { method: "DELETE" }); await refresh(); }
  return <main className="shell"><aside className="sidebar"><Link className="brand" href="/"><span className="brandName">BAYSYSTECH<small>ATLAS</small></span></Link><nav><Link href="/">⌂　Overview</Link><Link href="/tasks">◷　Tasks</Link><Link href="/approvals">✓　Approvals</Link><Link className="active" href="/memory">▤　Memory</Link><Link href="/audit">≡　Audit</Link><Link href="/schedules">⟳　Schedules</Link><Link href="/settings">⚙　Settings</Link></nav></aside><section className="content"><header><span>LONG-TERM CONTEXT</span><div className="profile">M</div></header><div className="settingsPage"><div className="eyebrow">PERSONAL MEMORY</div><h1>Memory</h1><p className="settingsIntro">Add facts or past-event notes Atlas can use to personalize future answers.</p><form className="memoryCreate" onSubmit={add}><label htmlFor="memoryContent">New memory</label><textarea id="memoryContent" value={content} onChange={(e) => setContent(e.target.value)} placeholder="For example: I prefer concise morning summaries…" /><div className="memoryActions"><select value={category} onChange={(e) => setCategory(e.target.value as "semantic" | "episodic")}><option value="semantic">Fact / preference</option><option value="episodic">Past event</option></select><button className="saveButton" disabled={!content.trim()}>Save memory</button></div></form><div className="memorySearch"><input aria-label="Search memory" value={query} onChange={(e) => { setQuery(e.target.value); void refresh(e.target.value); }} placeholder="Search saved memories…" /></div>{error && <div className="settingsError">{error}</div>}<div className="memoryList">{memories.length === 0 ? <div className="emptyPanel">No matching memories saved yet.</div> : memories.map((memory) => <article className="taskCard" key={memory.id}><div className="taskHeader"><span className="taskStatus">{memory.category}</span><time>{new Date(memory.updated_at).toLocaleDateString()}</time></div><p className="taskResult">{memory.content}</p><button className="removeButton" onClick={() => void remove(memory.id)}>Delete</button></article>)}</div></div><footer><span>ATLAS · LOCAL INSTANCE</span><span>Memory stays in the local database</span></footer></section></main>;
}
