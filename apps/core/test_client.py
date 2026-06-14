"""Test client helpers — Python 3.14 + Django 4.2 template context copy workaround."""
from django.test import Client
from django.test import client as django_test_client


def _safe_store_rendered_templates(store, signal, sender, template, context, **kwargs):
    """Record templates without copying context (copy breaks on Python 3.14)."""
    store.setdefault('templates', []).append(template)


# Apply once when tests import this module.
django_test_client.store_rendered_templates = _safe_store_rendered_templates

SafeClient = Client
