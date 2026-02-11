#!/usr/bin/env python
"""
Script de diagnostic pour MyKarfour sur Dokploy
"""
import os
import sys
import django
import subprocess
import socket

def test_django_setup():
    """Test la configuration Django"""
    print("=== 🐍 Test Django Setup ===")
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mykarfour_app.settings')
        django.setup()
        print("✅ Django setup: OK")
        return True
    except Exception as e:
        print(f"❌ Django setup: {e}")
        return False

def test_database_connection():
    """Test la connexion à la base de données"""
    print("\n=== 🗄️ Test Database Connection ===")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result[0] == 1:
                print("✅ Database connection: OK")
                return True
    except Exception as e:
        print(f"❌ Database connection: {e}")
        return False

def test_django_check():
    """Test la configuration Django complète"""
    print("\n=== 🔍 Django Check ===")
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'check'])
        print("✅ Django check: OK")
        return True
    except Exception as e:
        print(f"❌ Django check: {e}")
        return False

def test_migrations():
    """Test les migrations"""
    print("\n=== 📋 Test Migrations ===")
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'migrate', '--check'])
        print("✅ Migrations: OK")
        return True
    except Exception as e:
        print(f"❌ Migrations: {e}")
        return False

def test_static_files():
    """Test les fichiers statiques"""
    print("\n=== 📁 Test Static Files ===")
    try:
        from django.contrib.staticfiles.finders import find
        if find('css/style.css'):
            print("✅ Static files: OK")
            return True
        else:
            print("⚠️ Static files: Some files missing")
            return False
    except Exception as e:
        print(f"❌ Static files: {e}")
        return False

def test_server_bind():
    """Test si le serveur peut se binder sur le port 8000"""
    print("\n=== 🌐 Test Server Bind ===")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', 8000))
        sock.listen(1)
        sock.close()
        print("✅ Port 8000: Available")
        return True
    except Exception as e:
        print(f"❌ Port 8000: {e}")
        return False

def test_gunicorn():
    """Test Gunicorn directement"""
    print("\n=== 🦄 Test Gunicorn ===")
    try:
        result = subprocess.run([
            'gunicorn', 
            'mykarfour_app.wsgi:application', 
            '--bind', '0.0.0.0:8000',
            '--workers', '1',
            '--timeout', '30',
            '--check-config'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Gunicorn config: OK")
            return True
        else:
            print(f"❌ Gunicorn config: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Gunicorn test: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 MyKarfour - Diagnostic Dokploy")
    print("=" * 50)
    
    tests = [
        test_django_setup,
        test_database_connection,
        test_django_check,
        test_migrations,
        test_static_files,
        test_server_bind,
        test_gunicorn
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 RÉSULTATS:")
    print(f"✅ Tests réussis: {sum(results)}/{len(results)}")
    print(f"❌ Tests échoués: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 Tous les tests sont OK! Le problème vient probablement de:")
        print("   - Configuration du reverse proxy (Traefik)")
        print("   - Variables d'environnement manquantes")
        print("   - Network Docker")
    else:
        print("\n🔧 Corrigez les erreurs ci-dessus avant de déployer")

if __name__ == "__main__":
    main()
