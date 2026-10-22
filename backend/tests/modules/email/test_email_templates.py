import pytest

from app.modules.email.templates import render_email


def test_signup_welcome_renders_brand_and_links():
    html, text = render_email(
        "welcome_signup",
        first_name="Ada",
        dashboard_url="https://app.useoluora.xyz/dashboard",
    )
    assert "Welcome to OluOra, Ada" in html
    assert "#0B3D2E" in html  # brand deep-green masthead
    assert "#FED65B" in html  # the single gold accent rule
    assert "https://app.useoluora.xyz/dashboard" in html
    assert "<html" not in text
    assert "Ada" in text


def test_marketing_templates_include_unsubscribe_when_provided():
    html, text = render_email(
        "waitlist_welcome", unsubscribe_url="https://api.useoluora.xyz/unsub?token=abc"
    )
    assert "https://api.useoluora.xyz/unsub?token=abc" in html
    assert "https://api.useoluora.xyz/unsub?token=abc" in text


def test_transactional_template_has_no_unsubscribe_link():
    html, _ = render_email("waitlist_welcome")
    assert "Unsubscribe" not in html


def test_broadcast_renders_paragraphs_and_heading():
    html, text = render_email(
        "waitlist_broadcast",
        heading="We're live",
        paragraphs=["First paragraph.", "Second paragraph."],
    )
    assert "We&#39;re live" in html or "We're live" in html
    assert "First paragraph." in html
    assert "Second paragraph." in text


def test_feedback_reminder_links_to_dashboard():
    html, _ = render_email("feedback_reminder", feedback_url="https://app/x/dashboard")
    assert "https://app/x/dashboard" in html


def test_missing_template_raises():
    with pytest.raises(Exception):
        render_email("does_not_exist")
