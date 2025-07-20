def test_email_send_message():
    from app import log
    from app.common.email_sender import email_send_message

    """Test the email_send_message function."""
    subject = "Test Email"
    msg = "<h1>This is a test email</h1>"
    email_from = "sender@example.com"
    email_to = "recipient@example.com"
    result = email_send_message(
        subject=subject,
        msg=msg,
        email_from=email_from,
        email_to=email_to,
        msg_plain="This is a test email",
        email_to_cc=None,
        email_to_bcc=None,
        priority=3,
        attachments=["./pyproject.toml", "./README.md"],
    )
    log.info(f"Email sent successfully: {result}")
