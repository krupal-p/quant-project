# Do NOT rename this module to `email.py` as it will conflict with the standard library!

# import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app import log


def email_send_message(
    subject: str,
    msg: str,
    email_from: str,
    email_to: str | list[str],
    msg_plain: str | None = None,
    email_to_cc: str | list[str] | None = None,
    email_to_bcc: str | list[str] | None = None,
    priority: int = 3,
    attachments: str | Path | list[str | Path] | None = None,
    inline_images: dict[str, str] | None = None,
) -> MIMEMultipart:
    """Send an email message with optional HTML/plain content, attachments, and inline images.

    Parameters
    ----------
        subject (str): The subject of the email.
        msg (str): The HTML content of the email message.
        email_from (str): The sender's email address.
        email_to (str | list[str] ): Recipient(s) email address(es) for the "To" field.
        msg_plain (str | None, optional): The plain text version of the email message. Defaults to None.
        email_to_cc (str | list[str] | None, optional): Recipient(s) email address(es) for the "Cc" field. Defaults to None.
        email_to_bcc (str | list[str] | None, optional): Recipient(s) email address(es) for the "Bcc" field. Defaults to None.
        priority (int, optional): Email priority (1 = highest, 5 = lowest). Defaults to 3.
        attachments (str | list[str] | Path | list[Path] | None, optional): Filepath(s) to attach to the email. Defaults to None.
        inline_images (dict[str, str] | None, optional): Dictionary mapping Content-ID (cid) to image filepaths for inline images. Defaults to None.

    Returns
    -------
        email.message.Message: The constructed email message object.

    Raises
    ------
        ValueError: If none of email_to, email_to_cc, or email_to_bcc are specified.

    Logs:
        Logs the email parameters and content for debugging purposes.

    """
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = email_from

    email_to_dict = {"To": email_to, "Cc": email_to_cc, "Bcc": email_to_bcc}
    if all(val is None for val in email_to_dict.values()):
        msg = "One of email_to, email_to_cc, or email_to_bcc must be specified"
        raise ValueError(
            msg,
        )

    for key, val in email_to_dict.items():
        if isinstance(val, list):
            val = ", ".join(val)
        if val is not None:
            message[key] = val
    message["X-Priority"] = str(priority)

    # First add the message in plain text, then the HTML version;
    # email clients try to render the last part first
    if msg_plain:
        message.attach(MIMEText(msg_plain, "plain"))
    if msg:
        message.attach(MIMEText(msg, "html"))

    if attachments is None:
        attachments = []
    elif isinstance(attachments, str | Path):
        attachments = [attachments]

    # Ensure all attachments are Path objects
    path_attachments = [Path(a) if not isinstance(a, Path) else a for a in attachments]

    for filepath in path_attachments:
        with filepath.open("rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        filename = Path(filepath).name
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )
        message.attach(part)

    for cid, filepath in (inline_images or {}).items():
        with Path(filepath).open("rb") as img_file:
            img = MIMEImage(img_file.read())
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline")
            message.attach(img)

    # with smtplib.SMTP("localhost") as server:
    #     server.send_message(message)

    log.info(
        f"""
        Email sent with the following parameters:
        Subject: {subject}
        From: {email_from}
        To: {email_to}
        Cc: {email_to_cc}
        Bcc: {email_to_bcc}
        Priority: {priority}
        Attachments: {path_attachments}
        Inline Images: {inline_images}
        Message: {msg}
        Plain Text Message: {msg_plain}
""",
    )

    return message
