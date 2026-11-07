# Email templates

"""Templates for email notifications."""

# Setup email template
SETUP_EMAIL_TEMPLATE = """
Hello {admin_email},

Thank you for signing up for Cyantula!

Your instance has been provisioned and is ready for setup.

To complete the setup:

1. Click the link below (valid for 24 hours):
   {setup_url}

2. Follow the setup wizard to configure your instance

3. Once complete, you can access your Cyantula at:
   {instance_url}

If you have any questions, please contact support@example.com

Best regards,
The Cyantula Team
"""

# Welcome email template
WELCOME_EMAIL_TEMPLATE = """
Hello {admin_email},

Your Cyantula instance is now active!

You can access your instance at:
{instance_url}

Organisation: {organisation_name}
Admin email: {admin_email}

Quick start guide:
1. Add users to your organisation
2. Deploy your first app
3. Configure your environment variables

Need help? Contact support@example.com

Best regards,
The Cyantula Team
"""

# Deprovisioning notice template
DEPROVISIONING_NOTICE_TEMPLATE = """
Hello {admin_email},

This is a notice that your Cyantula instance will be deprovisioned on {deletion_date}.

Your instance: {organisation_name}
Last access: {last_access}

Before this date, please export any important data. After deprovisioning, all data will be permanently deleted.

If you wish to continue using Cyantula, please contact support@example.com to renew your subscription.

Best regards,
The Cyantula Team
"""

# Error notification template
ERROR_NOTIFICATION_TEMPLATE = """
Hello {admin_email},

We encountered an error provisioning your Cyantula instance.

Organisation: {organisation_name}
Error: {error_message}

Please try again or contact support@example.com for assistance.

Best regards,
The Cyantula Team
"""

# Template renderer
def render_template(template: str, **kwargs) -> str:
    """Render email template with provided data."""
    return template.format(**kwargs)
