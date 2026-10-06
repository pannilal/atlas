"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type AuditEntry = { id: string; action: string; entity_type: string; entity_id: string; details: Record<string, unknown>; created_at: string };

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  async function refresh() {
    try {
      const response = await fetch("/api/v1/audit?limit=200");
      if (!response.ok) throw new Error("Could not load the audit history.");
      setEntries(await response.json());
      setError("");
    } catch { setError("Atlas API is unavailable. The local audit history could not be loaded."); }
  }
  useEffect(() => { void refresh(); const timer = setInterval(() => void refresh(), 5000); return () => clearInterval(timer); }, []);
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return needle ? entries.filter((entry) => `${entry.action} ${entry.entity_type} ${entry.entity_id} ${JSON.stringify(entry.details)}`.toLowerCase().includes(needle)) : entries;
  }, [entries, query]);

  return <main className="shell"><aside className="sidebar"><Link className="brand" href="/"><span className="brandName">BAYSYSTECH<small>ATLAS</small></span></Link><nav><Link href="/">⌂　Overview</Link><Link href="/tasks">◷　Tasks</Link><Link href="/approvals">✓　Approvals</Link><Link href="/memory">▤　Memory</Link><Link className="active" href="/audit">≡　Audit</Link><Link href="/schedules">⟳　Schedules</Link><Link href="/settings">⚙　Settings</Link></nav></aside><section className="content"><header><span>ACTIVITY HISTORY</span><button className="newChat" onClick={() => void refresh()}>↻ Refresh</button><div className="profile">M</div></header><div className="settingsPage"><div className="eyebrow">LOCAL OBSERVABILITY</div><h1>Audit history</h1><p className="settingsIntro">Review task, approval, and tool activity recorded by Atlas on this computer.</p><div className="memorySearch"><input aria-label="Filter audit history" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter by action, task, tool, or detail…" /></div>{error && <div className="settingsError">{error}</div>}<div className="auditList">{filtered.length === 0 ? <div className="emptyPanel">{query ? "No audit entries match that filter." : "No activity has been recorded yet."}</div> : filtered.map((entry) => <article className="taskCard auditCard" key={entry.id}><div className="taskHeader"><span className="taskStatus">{entry.action}</span><time>{new Date(entry.created_at).toLocaleString()}</time></div><p className="auditEntity">{entry.entity_type} · {entry.entity_id}</p><pre>{JSON.stringify(entry.details, null, 2)}</pre></article>)}</div></div><footer><span>ATLAS · LOCAL INSTANCE</span><span>Showing the latest {Math.min(entries.length, 200)} of up to 200 audit entries</span></footer></section></main>;
}
