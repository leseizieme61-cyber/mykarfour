#!/usr/bin/env python
import os
import django
from django.conf import settings

print("=== Django Configuration Test ===")
print(f"Django version: {django.VERSION}")
print(f"Settings module: {settings.SETTINGS_MODULE}")
print(f"DEBUG: {settings.DEBUG}")
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"SECRET_KEY configured: {bool(settings.SECRET_KEY)}")
print(f"Database URL configured: {bool(hasattr(settings, 'DATABASE_URL') or hasattr(settings, 'DATABASES'))}")

try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        print("✅ Database connection: OK")
except Exception as e:
    print(f"❌ Database connection: {e}")

print("=== Test Complete ===")
