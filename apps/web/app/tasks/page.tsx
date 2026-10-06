"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type ToolExecution = { id: string; tool_name: string; status: string; created_at: string; completed_at?: string | null };
type Task = { id: string; instruction: string; status: string; browser_control?: string; created_at: string; result?: string | null; error?: string | null; tool_executions?: ToolExecution[] };

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function refresh() { try { const response = await fetch("/api/v1/tasks"); if (response.ok) setTasks(await response.json()); } catch { setError("Atlas API is unavailable."); } }
  useEffect(() => { void refresh(); const timer = setInterval(() => void refresh(), 2500); return () => clearInterval(timer); }, []);
  async function create(event: FormEvent) {
    event.preventDefault(); const text = instruction.trim(); if (!text || busy) return;
    setBusy(true); setError("");
    try { const response = await fetch("/api/v1/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ instruction: text }) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Could not create task."); setInstruction(""); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not create task."); }
    finally { setBusy(false); }
  }
  async function setBrowserControl(task: Task, action: "takeover" | "resume") {
    setError("");
    try {
      const response = await fetch(`/api/v1/tasks/${task.id}/browser-control/${action}`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not change browser control.");
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not change browser control."); }
  }
  return <main className="shell"><aside className="sidebar"><Link className="brand" href="/"><span className="brandName">BAYSYSTECH<small>ATLAS</small></span></Link><nav><Link href="/">⌂　Overview</Link><Link className="active" href="/tasks">◷　Tasks</Link><Link href="/approvals">✓　Approvals</Link><Link href="/memory">▤　Memory</Link><Link href="/audit">≡　Audit</Link><Link href="/schedules">⟳　Schedules</Link><Link href="/settings">⚙　Settings</Link></nav></aside><section className="content"><header><span>WORK QUEUE</span><div className="profile">M</div></header><div className="settingsPage"><div className="eyebrow">BACKGROUND WORK</div><h1>Tasks</h1><p className="settingsIntro">Start work that runs in the background and keeps its status and result here.</p><form className="taskCreate" onSubmit={create}><textarea aria-label="Task instruction" placeholder="Describe a task for Atlas…" value={instruction} onChange={(e) => setInstruction(e.target.value)} /><button className="saveButton" disabled={busy || !instruction.trim()}>{busy ? "Queueing…" : "Start task"}</button></form>{error && <div className="settingsError">{error}</div>}<div className="taskList">{tasks.length === 0 ? <div className="emptyPanel">No tasks yet. Describe something above to get started.</div> : tasks.map((task) => <article className="taskCard" key={task.id}><div className="taskHeader"><span className={`taskStatus ${task.status.toLowerCase()}`}>{task.status.replaceAll("_", " ")}</span><time>{new Date(task.created_at).toLocaleString()}</time></div><h2>{task.instruction}</h2>{task.result && <p className="taskResult">{task.result}</p>}{task.error && <p className="chatError">{task.error}</p>}{task.tool_executions?.length ? <div className="toolExecutions"><b>TOOL ACTIVITY</b>{task.tool_executions.map((tool) => <div className="toolExecution" key={tool.id}><span>{tool.tool_name.replaceAll("_", " ")}</span><span>{tool.status.replaceAll("_", " ")}</span></div>)}</div> : null}{task.tool_executions?.some((tool) => tool.tool_name === "browser_task" && ["RUNNING", "WAITING_APPROVAL"].includes(tool.status)) && <div className="browserControl"><p>{task.status === "WAITING_USER" ? "Browser is paused for you. Sign in or complete the step, then return control to Atlas." : "Atlas is working in a visible browser. You can take control at any time."}</p>{task.status === "WAITING_USER" ? <button className="saveButton" onClick={() => void setBrowserControl(task, "resume")}>Return control to Atlas</button> : <button className="cancelTask" onClick={() => void setBrowserControl(task, "takeover")}>Take control</button>}</div>}{["PENDING", "PLANNING", "RUNNING", "WAITING_APPROVAL", "WAITING_USER"].includes(task.status) && <button className="cancelTask" onClick={async () => { await fetch(`/api/v1/tasks/${task.id}/cancel`, { method: "POST" }); await refresh(); }}>Cancel</button>}</article>)}</div></div><footer><span>ATLAS · LOCAL INSTANCE</span><span>Tasks persist in your local database</span></footer></section></main>;
}
