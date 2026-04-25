from __future__ import annotations

from datetime import datetime
from email import message_from_bytes
from email.header import decode_header, make_header
from email.policy import default

from imapclient import IMAPClient


class ImapMailboxClient:
    def __init__(self, host: str, port: int, username: str, password: str, ssl: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ssl = ssl

    def fetch_inbox_emails(self, limit: int = 20) -> list[dict]:
        with IMAPClient(self.host, port=self.port, ssl=self.ssl) as client:
            client.login(self.username, self.password)
            client.select_folder("INBOX")
            message_ids = client.search(["ALL"])
            latest_ids = message_ids[-limit:]

            if not latest_ids:
                return []

            response = client.fetch(latest_ids, [b"ENVELOPE"])
            emails = []

            for uid in reversed(latest_ids):
                envelope = response[uid][b"ENVELOPE"]
                from_address = ""
                if envelope.from_:
                    sender = envelope.from_[0]
                    mailbox = _to_text(sender.mailbox)
                    host = _to_text(sender.host)
                    from_address = f"{mailbox}@{host}" if mailbox and host else ""

                emails.append(
                    {
                        "uid": uid,
                        "subject": _decode_subject(envelope.subject),
                        "from": from_address,
                        "date": _format_date(envelope.date),
                    }
                )

            return emails

    def fetch_email_detail(self, uid: int) -> dict:
        with IMAPClient(self.host, port=self.port, ssl=self.ssl) as client:
            client.login(self.username, self.password)
            client.select_folder("INBOX")
            response = client.fetch([uid], [b"RFC822", b"ENVELOPE", b"BODYSTRUCTURE"])

            if uid not in response:
                raise ValueError(f"Email with UID {uid} was not found.")

            message_bytes = response[uid][b"RFC822"]
            parsed_message = message_from_bytes(message_bytes, policy=default)
            envelope = response[uid].get(b"ENVELOPE")

            return {
                "uid": uid,
                "subject": _decode_subject(parsed_message.get("Subject") or (envelope.subject if envelope else None)),
                "from": _addresses_to_list(parsed_message.get_all("From", [])),
                "to": _addresses_to_list(parsed_message.get_all("To", [])),
                "cc": _addresses_to_list(parsed_message.get_all("Cc", [])),
                "date": _to_text(parsed_message.get("Date") or (envelope.date if envelope else "")),
                "message_id": _to_text(parsed_message.get("Message-ID")),
                "content_type": parsed_message.get_content_type(),
                "body": _extract_body(parsed_message),
                "headers": [{"name": key, "value": _to_text(value)} for key, value in parsed_message.items()],
            }


def _to_text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value or "")


def _decode_subject(subject) -> str:
    if not subject:
        return "(No subject)"
    try:
        return str(make_header(decode_header(_to_text(subject))))
    except Exception:
        return _to_text(subject)


def _format_date(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return _to_text(value)


def _addresses_to_list(values) -> list[str]:
    addresses = []
    for value in values:
        addresses.extend([item.strip() for item in _to_text(value).split(",") if item.strip()])
    return addresses


def _extract_body(message) -> dict:
    plain_parts = []
    html_parts = []

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_disposition() == "attachment":
                continue

            content_type = part.get_content_type()
            payload = _get_part_content(part)
            if not payload:
                continue

            if content_type == "text/plain":
                plain_parts.append(payload)
            elif content_type == "text/html":
                html_parts.append(payload)
    else:
        payload = _get_part_content(message)
        if message.get_content_type() == "text/html":
            html_parts.append(payload)
        else:
            plain_parts.append(payload)

    plain_text = "\n\n".join(part for part in plain_parts if part).strip()
    html_text = "\n\n".join(part for part in html_parts if part).strip()

    return {
        "plain": plain_text,
        "html": html_text,
        "preferred": plain_text or html_text or "",
    }


def _get_part_content(part) -> str:
    try:
        content = part.get_content()
    except Exception:
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    return _to_text(content)
