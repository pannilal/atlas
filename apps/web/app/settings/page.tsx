"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type Provider = "openai" | "anthropic" | "hackclub" | "hermes";
type Status = { provider: Provider; model: string; hermes_base_url: string; configured: boolean };
type PermissionMode = "review" | "unrestricted";

export default function SettingsPage() {
  const [provider, setProvider] = useState<Provider>("hackclub");
  const [model, setModel] = useState("openai/gpt-4o-mini");
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:8642/v1");
  const [apiKey, setApiKey] = useState("");
  const [configured, setConfigured] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [autoExtractMemories, setAutoExtractMemories] = useState(false);
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [memoryNotice, setMemoryNotice] = useState("");
  const [memoryError, setMemoryError] = useState("");
  const [permissionMode, setPermissionMode] = useState<PermissionMode>("review");
  const [selectedMode, setSelectedMode] = useState<PermissionMode>("review");
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const savedTheme = localStorage.getItem("atlas-theme");
    const useDark = savedTheme === "dark";
    setDarkMode(useDark);
    document.documentElement.dataset.theme = useDark ? "dark" : "light";
    fetch("/api/v1/settings/provider").then((r) => r.json()).then((d: Status) => { setProvider(d.provider); setModel(d.model); setBaseUrl(d.hermes_base_url); setConfigured(d.configured); }).catch(() => setError("Could not reach the Atlas API. Make sure it is running."));
    fetch("/api/v1/settings/security").then((r) => r.json()).then((d) => { setPermissionMode(d.permission_mode); setSelectedMode(d.reconfirmation_required ? "unrestricted" : d.permission_mode); }).catch(() => {});
    fetch("/api/v1/memory/settings").then((r) => r.json()).then((d) => setAutoExtractMemories(Boolean(d.auto_extract_completed_tasks))).catch(() => {});
  }, []);

  function setTheme(enabled: boolean) {
    setDarkMode(enabled);
    const theme = enabled ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("atlas-theme", theme);
  }

  async function saveProvider(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch("/api/v1/settings/provider", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider, model, hermes_base_url: baseUrl, api_key: apiKey || null }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not save provider settings.");
      setConfigured(data.configured); setApiKey(""); setNotice("Provider settings saved securely on this PC.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save provider settings."); }
    finally { setBusy(false); }
  }

  async function savePermissionMode(mode: PermissionMode) {
    setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch("/api/v1/settings/security", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ permission_mode: mode, acknowledge_unrestricted_risks: acknowledged }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not save access mode.");
      setPermissionMode(data.permission_mode); setSelectedMode(data.permission_mode); setAcknowledged(false);
      setNotice(mode === "unrestricted" ? "Unrestricted mode enabled for supported actions. Every email send still requires its own approval." : "Review mode enabled. Sensitive actions require your approval.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save access mode."); }
    finally { setBusy(false); }
  }

  async function removeKey() {
    setBusy(true); setError(""); setNotice("");
    try { const response = await fetch("/api/v1/settings/provider/key", { method: "DELETE" }); if (!response.ok) throw new Error("Could not remove the saved API key."); setConfigured(false); setNotice("Saved API key removed from Windows Credential Manager."); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not remove key."); }
    finally { setBusy(false); }
  }

  async function chooseProvider(value: Provider) {
    setBusy(true);
    setProvider(value);
    setApiKey("");
    setModel(value === "openai" ? "gpt-5.5" : value === "anthropic" ? "claude-sonnet-4-6" : value === "hackclub" ? "openai/gpt-4o-mini" : "hermes-agent");
    try { const response = await fetch(`/api/v1/settings/provider/key-status?provider=${value}`); const data = await response.json(); setConfigured(Boolean(data.configured)); }
    catch { setConfigured(false); }
    finally { setBusy(false); }
  }

  async function saveMemoryPreference() {
    setMemoryBusy(true); setMemoryError(""); setMemoryNotice("");
    try {
      const response = await fetch("/api/v1/memory/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ auto_extract_completed_tasks: autoExtractMemories }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not save memory preferences.");
      setAutoExtractMemories(Boolean(data.auto_extract_completed_tasks));
      setMemoryNotice(data.auto_extract_completed_tasks ? "Automatic memory extraction enabled." : "Automatic memory extraction disabled.");
    } catch (e) { setMemoryError(e instanceof Error ? e.message : "Could not save memory preferences."); }
    finally { setMemoryBusy(false); }
  }

  return <main className="shell">
    <aside className="sidebar"><Link className="brand" href="/"><span className="brandName">BAYSYSTECH<small>ATLAS</small></span></Link><nav><Link href="/">⌂　Overview</Link><Link href="/tasks">◷　Tasks</Link><Link href="/approvals">✓　Approvals</Link><Link href="/memory">▤　Memory</Link><Link className="active" href="/settings">⚙　Settings</Link></nav></aside>
    <section className="content"><header><span>PERSONAL WORKSPACE</span><Link href="/" className="backLink">←　Overview</Link></header>
      <div className="settingsPage"><div className="eyebrow">CONFIGURATION</div><h1>Settings</h1><p className="settingsIntro">Configure Atlas locally. Provider keys stay in Windows Credential Manager.</p>
        {error && <div className="settingsError" role="alert">{error}</div>}{notice && <div className="settingsNotice" role="status">{notice}</div>}
        <section className="settingsCard themeCard"><div><h2>Appearance</h2><p className="settingsHelp">Choose light or dark mode for this browser.</p></div><label className="themeToggle"><input type="checkbox" role="switch" checked={darkMode} onChange={(event) => setTheme(event.target.checked)} /><span>{darkMode ? "Dark mode" : "Light mode"}</span></label></section>
        <section className="settingsCard"><h2>AI provider</h2><p className="settingsHelp">Choose OpenAI, Anthropic, the Hack Club endpoint, or a local Hermes API server.</p><form onSubmit={saveProvider}>
          <label htmlFor="provider">Provider</label><select id="provider" value={provider} onChange={(event) => void chooseProvider(event.target.value as Provider)}><option value="hackclub">Hack Club AI proxy</option><option value="openai">OpenAI API</option><option value="anthropic">Anthropic Claude API</option><option value="hermes">Hermes local API</option></select>
          <label htmlFor="model">Model</label><input id="model" value={model} onChange={(event) => setModel(event.target.value)} required />
          {provider === "hermes" && <><label htmlFor="baseUrl">Hermes API URL</label><input id="baseUrl" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} required /><p className="fieldHelp">Hermes must be running on this PC with its API server enabled.</p></>}
          <label htmlFor="apiKey">{provider === "openai" ? "OpenAI API key" : provider === "anthropic" ? "Anthropic API key" : provider === "hackclub" ? "Hack Club API key" : "Hermes API key"}</label><input id="apiKey" type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={configured ? "Saved · leave blank to keep current key" : "Paste your API key"} autoComplete="new-password" required={!configured} /><p className="fieldHelp">The key is sent only to the local Atlas API, then stored in Windows Credential Manager.</p>
          <div className="settingsActions"><button className="saveButton" type="submit" disabled={busy}>{busy ? "Saving…" : "Save provider"}</button>{configured && <button className="removeButton" type="button" onClick={removeKey} disabled={busy}>Remove saved key</button>}</div>
        </form></section>
        <section className="settingsCard"><div className="eyebrow">LONG-TERM CONTEXT</div><h2>Automatic memory extraction</h2><p className="settingsHelp">When enabled, Atlas sends each completed task’s instruction and result to your selected AI provider to identify up to three useful, durable facts. Extracted memories are stored in your local database. Atlas skips obvious secrets and contact details; review or delete saved memories on the Memory page.</p><label className="memoryPreference"><input type="checkbox" checked={autoExtractMemories} onChange={(event) => setAutoExtractMemories(event.target.checked)} disabled={memoryBusy} /><span>Extract useful memories after completed tasks</span></label>{memoryError && <div className="settingsError" role="alert">{memoryError}</div>}{memoryNotice && <div className="settingsNotice" role="status">{memoryNotice}</div>}<div className="settingsActions"><button className="saveButton" onClick={() => void saveMemoryPreference()} disabled={memoryBusy}>{memoryBusy ? "Saving…" : "Save memory preference"}</button></div></section>
        <section className="settingsCard permissionCard"><div className="eyebrow">ACTION SAFETY</div><h2>Permission mode</h2><p className="settingsHelp">Choose whether Atlas should pause before sensitive actions.</p>
          <div className="permissionChoices"><label className={`permissionChoice ${selectedMode === "review" ? "selected" : ""}`}><input type="radio" name="permissionMode" checked={selectedMode === "review"} onChange={() => setSelectedMode("review")} disabled={busy} /><span><b>Review sensitive actions</b><small>Atlas asks for approval before supported high-impact actions. Recommended.</small></span></label><label className={`permissionChoice danger ${selectedMode === "unrestricted" ? "selected" : ""}`}><input type="radio" name="permissionMode" checked={selectedMode === "unrestricted"} onChange={() => { setSelectedMode("unrestricted"); setAcknowledged(false); }} disabled={busy} /><span><b>Unrestricted</b><small>Skip prompts for supported actions. Sending email always needs separate approval.</small></span></label></div>
          {selectedMode === "unrestricted" && permissionMode !== "unrestricted" && <><div className="warningPanel"><b>Unrestricted mode skips approval prompts for supported actions, with email sending always protected.</b> Atlas can read, create, or replace common text files in your Documents, Desktop, or Downloads folders; use a visible browser to navigate websites and interact with pages; and read Outlook Inbox and Sent Items. Atlas can send mail only after a separate approval showing the exact recipient, subject, and message body, even in Unrestricted mode. Mail, page, and file content may be sent to your selected AI provider. Actions run with your Windows account's permissions. Atlas does not delete or edit mail, execute downloaded files, or bypass Windows security.</div><label className="acknowledge"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span>I understand Atlas can access or change supported local files, interact with websites, and read Outlook messages without per-action approval, while every email send still requires approval.</span></label><button className="dangerButton" disabled={busy || !acknowledged} onClick={() => void savePermissionMode("unrestricted")}>{busy ? "Saving…" : "Enable unrestricted mode"}</button></>}
          {selectedMode === "review" && permissionMode === "unrestricted" && <div className="unrestrictedBanner"><b>Unrestricted mode is enabled.</b> Select save to restore approval prompts. <button onClick={() => void savePermissionMode("review")} disabled={busy}>Switch back to review mode</button></div>}
          {selectedMode === "unrestricted" && permissionMode === "unrestricted" && <div className="unrestrictedBanner"><b>Unrestricted mode is enabled.</b> Prompts are skipped for supported actions, but every email send still requires separate approval. <button onClick={() => { setSelectedMode("review"); void savePermissionMode("review"); }} disabled={busy}>Switch back to review mode</button></div>}
        </section>
      </div><footer><span>ATLAS · LOCAL INSTANCE</span><span>AI requests use your selected provider</span></footer>
    </section>
  </main>;
}
