"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@gmail.com', 'admin123')
        print("ADMIN CREATED ")
    else:
        u = User.objects.get(username='admin')
        u.set_password('admin123')
        u.is_staff = True
        u.is_superuser = True
        u.save()
        print("ADMIN RESET")
except Exception as e:
    print(f"Admin creation failed: {e}")