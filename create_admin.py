from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@gmail.com', 'admin123')
    print("Admin created")
else:
    print("Admin already exists")
    u = User.objects.get(username='admin')
    u.set_password('admin123')
    u.save()
    print("Password reset to admin123")