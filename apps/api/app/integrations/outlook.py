"""Read and send approved messages through the signed-in classic Outlook profile via Windows COM."""

import asyncio
import json
import re
from email.utils import parseaddr


def _search_outlook(query: str, unread_only: bool, max_results: int, folder_scope: str, chronology: str) -> str:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    outlook = namespace = items = None
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        matches = []
        needle = query.casefold().strip()
        scanned = 0
        folder_ids = {"inbox": (6,), "sent": (5,), "both": (6, 5)}[folder_scope]
        folder_names = {6: "Inbox", 5: "Sent Items"}
        scan_limit = max(40, max_results * 3) if not needle else 5000
        per_folder_limit = (max_results + len(folder_ids) - 1) // len(folder_ids)
        for folder_id in folder_ids:
            folder = namespace.GetDefaultFolder(folder_id)
            items = folder.Items
            items.Sort("[SentOn]" if folder_id == 5 else "[ReceivedTime]", chronology == "newest")
            indexes = range(1, min(items.Count, scan_limit) + 1)
            folder_matches = 0
            for index in indexes:
                item = items.Item(index)
                if getattr(item, "Class", 0) != 43:  # olMail
                    continue
                scanned += 1
                unread = bool(getattr(item, "UnRead", False))
                if unread_only and not unread:
                    continue
                subject = str(getattr(item, "Subject", "") or "")
                sender = str(getattr(item, "SenderName", "") or "")
                body = str(getattr(item, "Body", "") or "")
                haystack = f"{subject}\n{sender}\n{body}".casefold()
                if needle and needle not in haystack:
                    continue
                received = getattr(item, "SentOn" if folder_id == 5 else "ReceivedTime", None)
                matches.append({
                    "folder": folder_names[folder_id],
                    "date": received.isoformat() if received else None,
                    "sender": sender[:300],
                    "subject": subject[:500],
                    "unread": unread,
                    "body_preview": re.sub(r"\s+", " ", body).strip()[:1200],
                })
                folder_matches += 1
                if folder_matches >= per_folder_limit:
                    break
            items = None
            if len(matches) >= max_results:
                break
        if not matches:
            return json.dumps({"message": "No matching mail was found in the selected Outlook folders and range.", "scanned": scanned})
        return json.dumps({"folders": [folder_names[value] for value in folder_ids], "scanned": scanned, "messages": matches}, ensure_ascii=False)
    finally:
        items = None
        namespace = None
        outlook = None
        pythoncom.CoUninitialize()


async def search_outlook_mail(query: str = "", *, unread_only: bool = False, max_results: int = 10, folder_scope: str = "both", chronology: str = "newest") -> str:
    """Search Inbox and Sent Items without changing mail, flags, or folders."""
    if len(query) > 300:
        raise ValueError("Outlook search text must be at most 300 characters.")
    if not 1 <= max_results <= 20:
        raise ValueError("Choose between 1 and 20 messages to return.")
    if folder_scope not in {"inbox", "sent", "both"}:
        raise ValueError("Choose Inbox, Sent Items, or both Outlook folders.")
    if chronology not in {"newest", "oldest"}:
        raise ValueError("Choose newest or oldest messages.")
    try:
        return await asyncio.wait_for(asyncio.to_thread(_search_outlook, query, unread_only, max_results, folder_scope, chronology), timeout=60)
    except TimeoutError as exc:
        raise RuntimeError("Outlook did not respond within 60 seconds. Open classic Outlook and try again.") from exc
    except Exception as exc:
        raise RuntimeError(
            f"Classic Outlook mail access failed ({type(exc).__name__}). Make sure classic Outlook is installed, "
            "has a signed-in mail profile, and is available for this Windows account."
        ) from exc


def _send_outlook(to: list[str], cc: list[str], subject: str, body: str) -> str:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    outlook = message = None
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        message = outlook.CreateItem(0)  # olMailItem
        message.To = "; ".join(to)
        message.CC = "; ".join(cc)
        message.Subject = subject
        message.Body = body
        message.Send()
        return f"Outlook accepted the approved message for delivery to {', '.join(to)}."
    finally:
        message = None
        outlook = None
        pythoncom.CoUninitialize()


async def send_outlook_mail(to: list[str], cc: list[str], subject: str, body: str) -> str:
    """Send one explicitly approved message through the current classic Outlook profile."""
    if not to or len(to) > 20 or len(cc) > 20:
        raise ValueError("Provide 1 to 20 To recipients and at most 20 CC recipients.")
    for address in to + cc:
        parsed_name, parsed_address = parseaddr(address)
        if parsed_name or parsed_address != address.strip() or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", parsed_address):
            raise ValueError("Use explicit email addresses without display-name syntax.")
    if not subject.strip() or len(subject) > 500:
        raise ValueError("Email subject must be between 1 and 500 characters.")
    if not body.strip() or len(body) > 10000:
        raise ValueError("Email body must be between 1 and 10,000 characters.")
    try:
        return await asyncio.to_thread(_send_outlook, to, cc, subject, body)
    except Exception as exc:
        raise RuntimeError(
            f"Classic Outlook could not send the approved message ({type(exc).__name__}). Check that Outlook is open, "
            "has a signed-in mail profile, and can send mail for this Windows account."
        ) from exc
