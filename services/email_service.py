
import asyncio
import os
from azure.communication.email import EmailClient

connection_string = os.getenv("ACS_CONNECTION_STRING")
client = EmailClient.from_connection_string(connection_string) if connection_string else None


async def send_email(to_email: str, subject: str, html_content: str):
    global client
    if not client:
        cs = os.getenv("ACS_CONNECTION_STRING")
        if not cs:
            raise ValueError("ACS_CONNECTION_STRING not set")
        client = EmailClient.from_connection_string(cs)

    sender = os.getenv("ACS_SENDER_EMAIL")
    if not sender:
        raise ValueError("ACS_SENDER_EMAIL not set")

    message = {
        "senderAddress": sender,
        "recipients": {"to": [{"address": to_email}]},
        "content": {"subject": subject, "html": html_content},
    }

    # Run the blocking Azure SDK call in a thread so it doesn't freeze the event loop.
    # Without this, all concurrency from the semaphore is lost.
    def _blocking_send():
        poller = client.begin_send(message)
        return poller.result()

    return await asyncio.to_thread(_blocking_send)
