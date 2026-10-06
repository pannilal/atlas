"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Approval = { id: string; task_id: string; action: string; description: string; status: string; created_at: string };

export default function ApprovalsPage() {
  const [items, setItems] = useState<Approval[]>([]);
  const [error, setError] = useState("");
  async function refresh() { try { const response = await fetch("/api/v1/approvals"); if (response.ok) setItems(await response.json()); else setError("Could not load approvals."); } catch { setError("Atlas API is unavailable."); } }
  useEffect(() => { void refresh(); const timer = setInterval(() => void refresh(), 3000); return () => clearInterval(timer); }, []);
  async function decide(id: string, decision: "approve" | "reject") { const response = await fetch(`/api/v1/approvals/${id}/${decision}`, { method: "POST" }); if (!response.ok) { setError("This approval could not be updated."); return; } await refresh(); }
  const pending = items.filter((item) => item.status === "PENDING");
  return <main className="shell"><aside className="sidebar"><Link className="brand" href="/"><span className="brandName">BAYSYSTECH<small>ATLAS</small></span></Link><nav><Link href="/">⌂　Overview</Link><Link href="/tasks">◷　Tasks</Link><Link className="active" href="/approvals">✓　Approvals</Link><Link href="/memory">▤　Memory</Link><Link href="/audit">≡　Audit</Link><Link href="/schedules">⟳　Schedules</Link><Link href="/settings">⚙　Settings</Link></nav></aside><section className="content"><header><span>HUMAN IN THE LOOP</span><div className="profile">M</div></header><div className="settingsPage"><div className="eyebrow">YOUR CONTROL</div><h1>Approvals</h1><p className="settingsIntro">Review requested actions. Atlas will never perform an action that is waiting for approval until you approve it.</p>{error && <div className="settingsError">{error}</div>}{pending.length === 0 ? <div className="emptyPanel">Nothing is waiting for approval.</div> : pending.map((item) => <article className="taskCard" key={item.id}><span className="taskStatus waiting_for_approval">AWAITING APPROVAL</span><h2>{item.action}</h2><p className="taskResult">{item.description}</p><div className="settingsActions"><button className="saveButton" onClick={() => void decide(item.id, "approve")}>Approve</button><button className="removeButton" onClick={() => void decide(item.id, "reject")}>Reject</button></div></article>)}<h2 className="sectionSubheading">Recent decisions</h2>{items.filter((item) => item.status !== "PENDING").map((item) => <article className="taskCard compact" key={item.id}><span className="taskStatus">{item.status}</span><h2>{item.action}</h2><p className="taskResult">{item.description}</p></article>)}</div><footer><span>ATLAS · LOCAL INSTANCE</span><span>Protected actions require your approval</span></footer></section></main>;
}
