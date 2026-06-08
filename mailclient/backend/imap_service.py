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

            batch_size = 50
            emails = []
            
            for i in range(0, len(latest_ids), batch_size):
                batch_ids = latest_ids[i:i + batch_size]
                response = client.fetch(batch_ids, [b"ENVELOPE"])
                
                for uid in batch_ids:
                    if uid not in response:
                        continue
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
                            "message_id": _to_text(envelope.message_id),
                            "subject": _decode_subject(envelope.subject),
                            "from": from_address,
                            "date": _format_date(envelope.date),
                        }
                    )

            emails.reverse()
            return emails

    def fetch_email_detail(self, uid: int) -> dict:
        try:
            with IMAPClient(self.host, port=self.port, ssl=self.ssl) as client:
                client.login(self.username, self.password)
                client.select_folder("INBOX")
                response = client.fetch([uid], [b"BODY.PEEK[]"])

                if uid not in response:
                    raise ValueError(f"Email with UID {uid} was not found.")

                message_bytes = response[uid].get(b"BODY[]", b"")
        except Exception as e:
            if "EOF" in str(e):
                # Fallback to headers only if full payload kills connection
                with IMAPClient(self.host, port=self.port, ssl=self.ssl) as client2:
                    client2.login(self.username, self.password)
                    client2.select_folder("INBOX")
                    response = client2.fetch([uid], [b"BODY.PEEK[HEADER]"])
                    if uid not in response:
                        raise ValueError(f"Email with UID {uid} was not found.")
                    message_bytes = response[uid].get(b"BODY[HEADER]", b"")
                    message_bytes += b"\r\n\r\n[Warning: El servidor IMAP rechazo transmitir el contenido completo de este correo, probablemente por un archivo adjunto muy grande o bloqueo de antivirus. Solo se pudieron recuperar los encabezados.]"
            else:
                raise

        parsed_message = message_from_bytes(message_bytes, policy=default)
        envelope = None

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
