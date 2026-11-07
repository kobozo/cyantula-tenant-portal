# Email service for tenant onboarding

"""Email service for tenant setup notifications."""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dataclasses import dataclass


@dataclass
class EmailConfig:
    """Email configuration."""
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = "noreply@example.com"
    smtp_password: str = ""
    smtp_from: str = "noreply@example.com"
    use_tls: bool = True


class EmailService:
    """Service for sending email notifications."""
    
    def __init__(self, config: EmailConfig = EmailConfig()):
        self.config = config
    
    def _send_email(self, to: str, subject: str, body: str, html: Optional[str] = None) -> bool:
        """Send email with SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.config.smtp_from
            msg["To"] = to
            msg["Subject"] = subject
            
            # Text version
            part1 = MIMEText(body, "plain")
            msg.attach(part1)
            
            # HTML version (optional)
            if html:
                part2 = MIMEText(html, "html")
                msg.attach(part2)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.sendmail(self.config.smtp_from, to, msg.as_string())
            
            return True
            
        except Exception as e:
            print(f"[EMAIL] Error sending email: {e}")
            return False
    
    def send_setup_email(self, organisation, token: str) -> bool:
        """Send setup email to tenant admin."""
        dns_name = f"{organisation.slug}.cyantula.eu"
        
        setup_url = f"https://{dns_name}/setup?token={token}"
        
        text_body = f"""
Hello {organisation.admin_email},

Thank you for signing up for Cyantula!

Your instance has been provisioned and is ready for setup.

To complete the setup:

1. Click the link below (valid for 24 hours):
   {setup_url}

2. Follow the setup wizard to configure your instance

3. Once complete, you can access your Cyantula at:
   https://{dns_name}

If you have any questions, please contact support@example.com

Best regards,
The Cyantula Team
"""
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background-color: #f4f4f4;
            padding: 30px;
            border-radius: 10px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 16px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Welcome to Cyantula!</h2>
        <p>Hello {organisation.admin_email},</p>
        
        <p>Thank you for signing up for Cyantula! Your tenant instance has been provisioned and is ready for setup.</p>
        
        <h3>To complete setup:</h3>
        <ol>
            <li>Click the button below (valid for 24 hours):</li>
            <li>Follow the setup wizard to configure your instance</li>
            <li>Once complete, access your Cyantula at: <code>https://{dns_name}</code></li>
        </ol>
        
        <a href="{setup_url}" class="button">Complete Setup</a>
        
        <p><strong>Your instance details:</strong></p>
        <ul>
            <li>Instance URL: <a href="https://{dns_name}">https://{dns_name}</a></li>
            <li>Admin email: {organisation.admin_email}</li>
            <li>Organisation: {organisation.name}</li>
        </ul>
        
        <p>If you have any questions, please contact <a href="mailto:support@example.com">support@example.com</a></p>
        
        <div class="footer">
            <p>Cyantula Tenant Portal | Multi-tenant AI platform</p>
            <p>This is an automated message. Please do not reply directly to this email.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return self._send_email(
            to=organisation.admin_email,
            subject=f"Setup your Cyantula instance for {organisation.name}",
            body=text_body,
            html=html_body
        )
    
    def send_welcome_email(self, organisation) -> bool:
        """Send welcome email after setup completion."""
        dns_name = f"{organisation.slug}.cyantula.eu"
        
        text_body = f"""
Hello {organisation.admin_email},

Your Cyantula instance is now active!

You can access your instance at:
https://{dns_name}

Organisation: {organisation.name}
Admin email: {organisation.admin_email}

Quick start guide:
1. Add users to your organisation
2. Deploy your first app
3. Configure your environment variables

Need help? Contact support@example.com

Best regards,
The Cyantula Team
"""
        
        return self._send_email(
            to=organisation.admin_email,
            subject=f"Welcome to Cyantula, {organisation.name}!",
            body=text_body
        )
    
    def send_expiration_warning(self, organisation, days_left: int) -> bool:
        """Send warning about setup token expiration."""
        dns_name = f"{organisation.slug}.cyantula.eu"
        
        text_body = f"""
Hello {organisation.admin_email},

This is a reminder that your Cyantula setup is about to expire.

Your setup token will expire in {days_left} day(s).
You can still access your instance at:
https://{dns_name}

If you haven't completed setup yet, please log in soon to avoid any delays.

Best regards,
The Cyantula Team
"""
        
        return self._send_email(
            to=organisation.admin_email,
            subject=f"Setup expiration reminder - {days_left} day(s) remaining",
            body=text_body
        )
    
    def send_deprovisioning_notice(self, organisation, deletion_date) -> bool:
        """Send notice about tenant deprovisioning."""
        text_body = f"""
Hello {organisation.admin_email},

This is a notice that your Cyantula instance will be deprovisioned on {deletion_date}.

Your instance: {organisation.name}
Last access: {organisation.last_access_at if hasattr(organisation, 'last_access_at') else 'Unknown'}

Before this date, please export any important data. After deprovisioning, all data will be permanently deleted.

If you wish to continue using Cyantula, please contact support@example.com to renew your subscription.

Best regards,
The Cyantula Team
"""
        
        return self._send_email(
            to=organisation.admin_email,
            subject=f"Notice: Your Cyantula instance will be deprovisioned on {deletion_date}",
            body=text_body
        )


# Convenience function
def create_email_service(
    smtp_host: str = "smtp.example.com",
    smtp_port: int = 587,
    smtp_user: str = "noreply@example.com",
    smtp_password: str = ""
) -> EmailService:
    """Create email service with configuration."""
    config = EmailConfig(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password
    )
    return EmailService(config)
