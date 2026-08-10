from flask import render_template, current_app
from flask_mail import Message
from app import mail


def send_email(subject, recipients, text_body=None, html_body=None):
    """Send email using Flask-Mail. recipients is a list of addresses."""
    try:
        msg = Message(subject=subject, recipients=recipients)
        if html_body:
            msg.html = html_body
        if text_body:
            msg.body = text_body
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.exception('Failed to send email: %s', e)
        return False
