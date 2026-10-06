import type { Metadata } from "next";
import "./globals.css";
import "./interactive.css";
import "./workflows.css";
import "./audit.css";

export const metadata: Metadata = { title: "BaysysTech Atlas", description: "Your local-first AI agent workspace" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: `try{document.documentElement.dataset.theme=localStorage.getItem("atlas-theme")==="dark"?"dark":"light"}catch{}` }} /></head><body>{children}</body></html>;
}
