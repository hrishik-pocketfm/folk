from django.contrib.auth.backends import BaseBackend
from .models import User


class PhoneNumberBackend(BaseBackend):
    def authenticate(self, request, phone_number=None, **kwargs):
        try:
            user = User.objects.get(phone_number=phone_number, is_active=True)
            return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
