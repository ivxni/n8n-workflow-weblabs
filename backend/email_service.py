"""
Weblabs Lead Generator - Email Service

Async SMTP email delivery with HTML conversion and BCC self-copy.
"""

import os
import aiosmtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SMTP Konfiguration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

SENDER_NAME = os.getenv("SENDER_NAME", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    company_name: str = ""
) -> bool:
    """Sends an email via SMTP with both plain text and HTML parts."""
    
    if not SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD not configured - simulating send")
        return True
    
    try:
        message = MIMEMultipart("alternative")
        message["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject
        message["Bcc"] = SENDER_EMAIL
        
        recipients = [to_email, SENDER_EMAIL]
        
        text_part = MIMEText(body, "plain", "utf-8")
        message.attach(text_part)
        
        html_body = _text_to_html(body)
        html_part = MIMEText(html_body, "html", "utf-8")
        message.attach(html_part)
        
        use_tls = SMTP_PORT == 465
        
        logger.info(f"Connecting to SMTP: {SMTP_HOST}:{SMTP_PORT} (TLS: {use_tls})")
        
        await aiosmtplib.send(
            message,
            recipients=recipients,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            use_tls=use_tls,
            start_tls=not use_tls,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            timeout=10.0,
        )
        
        logger.info(f"Email sent to {company_name} ({to_email})")
        return True
        
    except aiosmtplib.SMTPRecipientsRefused as e:
        logger.error(f"Recipients refused: {e}")
        return False
    except aiosmtplib.SMTPAuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        return False
    except aiosmtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected send error: {e}")
        return False


def _text_to_html(text: str) -> str:
    """Converts plain text paragraphs to simple HTML."""
    paragraphs = text.split("\n\n")
    html_paragraphs = []
    
    for p in paragraphs:
        lines = p.replace("\n", "<br>")
        html_paragraphs.append(f"<p>{lines}</p>")
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            p {{
                margin: 0 0 1em 0;
            }}
        </style>
    </head>
    <body>
        {"".join(html_paragraphs)}
    </body>
    </html>
    """

async def send_test_email() -> bool:
    """Sends a test email to the configured sender address."""
    return await send_email(
        to_email=SENDER_EMAIL,
        subject="Weblabs Lead Generator - Test Email",
        body="Test successful!",
        company_name="Test",
    )
