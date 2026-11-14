from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'telephone', 'is_active')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Smart Baladiya', {'fields': ('role', 'telephone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Smart Baladiya', {'fields': ('first_name', 'last_name', 'email', 'role', 'telephone')}),
    )