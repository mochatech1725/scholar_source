"""
Email Service

Handles sending email notifications when jobs complete.
Uses Resend for email delivery.
"""

import os
from typing import List, Dict, Any
import resend
from dotenv import load_dotenv

load_dotenv()


def send_results_email(
    to_email: str,
    search_title: str,
    resources: List[Dict[str, Any]],
    job_id: str
) -> bool:
    """
    Send results email when job completes.

    Args:
        to_email: Recipient email address
        search_title: User-friendly name for the search
        resources: List of discovered resources
        job_id: UUID of completed job

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    resend_api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("FROM_EMAIL", "onboarding@resend.dev")

    # Skip if Resend not configured
    if not resend_api_key:
        print(f"⚠️  Resend API key not configured, skipping email to {to_email}")
        return False

    # Set API key
    resend.api_key = resend_api_key

    try:
        # Build email HTML content
        html_content = _build_email_html(search_title, resources, job_id)

        # Send email using Resend
        params = {
            "from": from_email,
            "to": [to_email],
            "subject": f"📚 Your ScholarSource Results: {search_title}",
            "html": html_content,
        }

        response = resend.Emails.send(params)

        print(f"✅ Email sent successfully to {to_email} (ID: {response.get('id', 'unknown')})")
        return True

    except Exception as e:
        print(f"❌ Error sending email to {to_email}: {str(e)}")
        return False


def _build_email_html(
    search_title: str,
    resources: List[Dict[str, Any]],
    job_id: str
) -> str:
    """
    Build HTML email content.

    Args:
        search_title: User-friendly name for the search
        resources: List of discovered resources
        job_id: UUID of completed job

    Returns:
        str: HTML email content
    """
    # Build resource list HTML
    resources_html = ""
    for resource in resources:
        resource_type = resource.get("type", "Resource")
        title = resource.get("title", "Untitled")
        url = resource.get("url", "#")
        source = resource.get("source", "Unknown")
        description = resource.get("description", "")

        resources_html += f"""
        <div style="margin-bottom: 20px; padding: 15px; background-color: #f9fafb; border-left: 4px solid #3b82f6; border-radius: 4px;">
            <div style="margin-bottom: 8px;">
                <span style="display: inline-block; padding: 4px 8px; background-color: #dbeafe; color: #1e40af; border-radius: 4px; font-size: 12px; font-weight: 600; margin-right: 8px;">
                    {resource_type}
                </span>
                <strong style="font-size: 16px; color: #1f2937;">{title}</strong>
            </div>
            <div style="margin-bottom: 8px;">
                <a href="{url}" style="color: #3b82f6; text-decoration: none; word-break: break-all;">
                    {url}
                </a>
            </div>
            <div style="color: #6b7280; font-size: 14px;">
                <strong>Source:</strong> {source}
            </div>
            {f'<div style="margin-top: 8px; color: #4b5563; font-size: 14px;">{description}</div>' if description else ''}
        </div>
        """

    # Build full email HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your ScholarSource Results</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1f2937; background-color: #f3f4f6; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px 30px;">
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="margin: 0; font-size: 28px; color: #1f2937;">📚 ScholarSource</h1>
                <p style="margin: 10px 0 0 0; color: #6b7280;">Your educational resources are ready!</p>
            </div>

            <!-- Search Title -->
            <div style="background-color: #eff6ff; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
                <h2 style="margin: 0 0 10px 0; font-size: 20px; color: #1e40af;">
                    {search_title}
                </h2>
                <p style="margin: 0; color: #6b7280; font-size: 14px;">
                    We found {len(resources)} resource{"s" if len(resources) != 1 else ""} for you
                </p>
            </div>

            <!-- Resources -->
            <div style="margin-bottom: 30px;">
                <h3 style="margin: 0 0 20px 0; font-size: 18px; color: #1f2937;">Discovered Resources</h3>
                {resources_html}
            </div>

            <!-- NotebookLM Tip -->
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 4px; margin-bottom: 30px;">
                <p style="margin: 0; color: #92400e; font-size: 14px;">
                    💡 <strong>Tip:</strong> Copy the URLs above and paste them into
                    <a href="https://notebooklm.google.com" style="color: #b45309; text-decoration: none;">Google NotebookLM</a>
                    to create flashcards, study guides, and quizzes from these resources.
                </p>
            </div>

            <!-- Footer -->
            <div style="text-align: center; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                    Job ID: {job_id}
                </p>
                <p style="margin: 10px 0 0 0; color: #9ca3af; font-size: 12px;">
                    This email was sent because you requested results from ScholarSource.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    return html
