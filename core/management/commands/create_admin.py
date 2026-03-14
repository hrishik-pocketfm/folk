from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create the default admin user (phone: 8999145848)'

    def handle(self, *args, **options):
        User = get_user_model()
        phone = '8999145848'
        if not User.objects.filter(phone_number=phone).exists():
            User.objects.create_superuser(
                phone_number=phone,
                name='Admin',
                is_staff=True,
                is_superuser=True,
                is_admin=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Admin user created (phone: {phone})'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin user already exists (phone: {phone})'))
