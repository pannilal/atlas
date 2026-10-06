"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type Job = { id: string; name: string; instruction: string; interval_seconds: number | null; cron_expression: string | null; timezone: string; enabled: boolean; next_run_at: string | null; created_at: string };

function intervalName(seconds: number) { if (seconds % 86400 === 0) return `Every ${seconds / 86400} day${seconds === 86400 ? "" : "s"}`; if (seconds % 3600 === 0) return `Every ${seconds / 3600} hour${seconds === 3600 ? "" : "s"}`; return `Every ${seconds / 60} minute${seconds === 60 ? "" : "s"}`; }

export default function SchedulesPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [name, setName] = useState("");
  const [instruction, setInstruction] = useState("");
  const [interval, setIntervalSeconds] = useState(3600);
  const [mode, setMode] = useState<"interval" | "cron">("interval");
  const [cronExpression, setCronExpression] = useState("0 8 * * 1-5");
  const [timezone, setTimezone] = useState(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function refresh() {
    try { const response = await fetch("/api/v1/schedules"); if (!response.ok) throw new Error(); setJobs(await response.json()); }
    catch { setError("Could not load recurring jobs. Check that Atlas is running."); }
  }
  useEffect(() => { void refresh(); const timer = globalThis.setInterval(() => void refresh(), 10000); return () => clearInterval(timer); }, []);
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const schedule = mode === "interval" ? { interval_seconds: interval } : { cron_expression: cronExpression, timezone };
      const response = await fetch("/api/v1/schedules", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, instruction, ...schedule }) });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Could not create the recurring job.");
      setName(""); setInstruction(""); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not create the recurring job."); }
    finally { setBusy(false); }
  }

  function jobScheduleName(job: Job) { return job.interval_seconds ? intervalName(job.interval_seconds) : `${job.cron_expression} · ${job.timezone}`; }
  async function setEnabled(job: Job, enabled: boolean) {
    const response = await fetch(`/api/v1/schedules/${job.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) });
    if (!response.ok) setError("Could not update this recurring job."); else await refresh();
  }
  async function remove(job: Job) {
    if (!window.confirm(`Delete the recurring job “${job.name}”?`)) return;
    const response = await fetch(`/api/v1/schedules/${job.id}`, { method: "DELETE" });
    if (!response.ok) setError("Could not delete this recurring job."); else await refresh();
  }

  return <main className="shell"><aside className="sidebar"><Link className="brand" href="/"><span className="brandName">BAYSYSTECH<small>ATLAS</small></span></Link><nav><Link href="/">⌂　Overview</Link><Link href="/tasks">◷　Tasks</Link><Link href="/approvals">✓　Approvals</Link><Link href="/memory">▤　Memory</Link><Link href="/audit">≡　Audit</Link><Link className="active" href="/schedules">⟳　Schedules</Link><Link href="/settings">⚙　Settings</Link></nav></aside><section className="content"><header><span>RECURRING WORK</span><div className="profile">M</div></header><div className="settingsPage"><div className="eyebrow">AUTOMATION</div><h1>Schedules</h1><p className="settingsIntro">Create recurring tasks. Atlas runs them locally while this computer and Atlas are on.</p><form className="scheduleCreate" onSubmit={create}><label htmlFor="scheduleName">Job name</label><input id="scheduleName" value={name} onChange={(e) => setName(e.target.value)} maxLength={200} required placeholder="Morning briefing" /><label htmlFor="scheduleInstruction">What should Atlas do?</label><textarea id="scheduleInstruction" value={instruction} onChange={(e) => setInstruction(e.target.value)} required placeholder="Summarize my saved tasks and list priorities…" /><label htmlFor="scheduleMode">Schedule type</label><select id="scheduleMode" value={mode} onChange={(e) => setMode(e.target.value as "interval" | "cron")}><option value="interval">Simple interval</option><option value="cron">Cron schedule</option></select>{mode === "interval" ? <><label htmlFor="scheduleInterval">Repeat</label><select id="scheduleInterval" value={interval} onChange={(e) => setIntervalSeconds(Number(e.target.value))}><option value={3600}>Every hour</option><option value={86400}>Every day</option><option value={604800}>Every week</option></select></> : <><label htmlFor="cronExpression">Cron expression (minute hour day month weekday)</label><input id="cronExpression" value={cronExpression} onChange={(e) => setCronExpression(e.target.value)} required placeholder="0 8 * * 1-5" /><span className="scheduleNext">Example: 0 8 * * 1-5 runs weekdays at 8:00 AM.</span><label htmlFor="scheduleTimezone">Timezone</label><input id="scheduleTimezone" value={timezone} onChange={(e) => setTimezone(e.target.value)} required placeholder="Asia/Kolkata" /></>}<button className="saveButton" disabled={busy || !name.trim() || !instruction.trim() || (mode === "cron" && !cronExpression.trim())}>{busy ? "Saving…" : "Create recurring job"}</button></form>{error && <div className="settingsError">{error}</div>}<div className="scheduleList">{jobs.length === 0 ? <div className="emptyPanel">No recurring jobs yet.</div> : jobs.map((job) => <article className="taskCard" key={job.id}><div className="taskHeader"><span className={`taskStatus ${job.enabled ? "completed" : "cancelled"}`}>{job.enabled ? "ACTIVE" : "PAUSED"}</span><time>{jobScheduleName(job)}</time></div><h2>{job.name}</h2><p className="taskResult">{job.instruction}</p><p className="scheduleNext">{job.enabled && job.next_run_at ? `Next run: ${new Date(job.next_run_at).toLocaleString(undefined, { timeZone: job.timezone })} (${job.timezone})` : "This job will not run until resumed."}</p><div className="scheduleActions"><button className="saveButton" onClick={() => void setEnabled(job, !job.enabled)}>{job.enabled ? "Pause" : "Resume"}</button><button className="removeButton" onClick={() => void remove(job)}>Delete</button></div></article>)}</div></div><footer><span>ATLAS · LOCAL INSTANCE</span><span>Jobs are stored in your local database</span></footer></section></main>;
}
