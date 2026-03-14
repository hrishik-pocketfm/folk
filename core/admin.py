from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Student, StudentSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('name', 'phone_number', 'is_admin', 'is_active')
    ordering = ('name',)
    search_fields = ('phone_number', 'name')
    filter_horizontal = ()
    list_filter = ('is_admin', 'is_active')
    fieldsets = (
        (None, {'fields': ('phone_number', 'name')}),
        ('Permissions', {'fields': ('is_admin', 'is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'name', 'is_admin'),
        }),
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'occupation', 'created_by', 'created_at')
    search_fields = ('name', 'phone_number')
    list_filter = ('created_by',)


@admin.register(StudentSession)
class StudentSessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'session_type', 'date_attended', 'added_by')
    list_filter = ('session_type',)
    search_fields = ('student__name',)
