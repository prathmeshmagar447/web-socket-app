# notifications/email_notifier.py
import smtplib
from email.mime.text import MIMEText
from config import Config

class EmailNotifier:
    def send_email(self, to_email, subject, body):
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = Config.EMAIL_SENDER
            msg['To'] = to_email

            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
                server.sendmail(Config.EMAIL_SENDER, [to_email], msg.as_string())
            print(f"✅ Email sent to {to_email}")
            return True
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False

email_notifier = EmailNotifier()
