from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings


class UserManager(BaseUserManager):
    def create_user(self, phone_number, name, **extra_fields):
        if not phone_number:
            raise ValueError('Phone number is required')
        user = self.model(phone_number=phone_number, name=name, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, name, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number, name, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=15, unique=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


SESSION_CHOICES = [
    ('L1', 'Vedic Science Level 1'),
    ('L2', 'Vedic Science Level 2'),
    ('L3', 'Vedic Science Level 3'),
    ('FOLK', 'FOLK Sessions'),
]


class Student(models.Model):
    name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=15, blank=True)
    occupation = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='students_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def attended_session_types(self):
        return set(self.sessions.values_list('session_type', flat=True))


class StudentSession(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    session_type = models.CharField(max_length=10, choices=SESSION_CHOICES)
    date_attended = models.DateField()
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sessions_added'
    )

    class Meta:
        unique_together = ('student', 'session_type')
        ordering = ['date_attended']

    def __str__(self):
        return f"{self.student.name} — {self.get_session_type_display()}"
