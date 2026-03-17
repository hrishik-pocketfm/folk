from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.db.models import Case, When, Value, IntegerField

RATING_PRIORITY = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}

def higher_rating(r1, r2):
    """Return whichever rating is higher (HIGH beats MEDIUM beats LOW)."""
    return r1 if RATING_PRIORITY.get(r1, 0) >= RATING_PRIORITY.get(r2, 0) else r2

RATING_SORT = Case(
    When(rating='HIGH',   then=Value(0)),
    When(rating='MEDIUM', then=Value(1)),
    When(rating='LOW',    then=Value(2)),
    default=Value(3),
    output_field=IntegerField(),
)


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

RATING_CHOICES = [
    ('HIGH', 'High'),
    ('MEDIUM', 'Medium'),
    ('LOW', 'Low'),
]


class Student(models.Model):
    name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=15, blank=True)
    occupation = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    rating = models.CharField(max_length=10, choices=RATING_CHOICES, default='MEDIUM')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='students_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def wa_number(self):
        """Return WhatsApp-ready 12-digit Indian number (e.g. 918999145848)."""
        digits = ''.join(c for c in self.phone_number if c.isdigit())
        if len(digits) == 10:
            return '91' + digits
        if len(digits) == 11 and digits.startswith('0'):
            return '91' + digits[1:]
        if len(digits) == 12 and digits.startswith('91'):
            return digits
        return '91' + digits[-10:] if len(digits) >= 10 else digits

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
        # unique_together removed: FOLK is a continuous program (multiple attendances allowed).
        # Uniqueness for L1/L2/L3 is enforced in the view layer.
        ordering = ['date_attended']

    def __str__(self):
        return f"{self.student.name} — {self.get_session_type_display()}"
