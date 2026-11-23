from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from .models import User

class SuperuserAdminSite(AdminSite):
    site_header = "Site administration"
    index_title = "Administration"
    site_title = "Smart Baladiya"

    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser


smart_admin_site = SuperuserAdminSite(name="smart_admin")

@admin.register(User, site=smart_admin_site)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'telephone', 'is_active')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Smart Baladiya', {'fields': ('role', 'telephone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Smart Baladiya', {'fields': ('first_name', 'last_name', 'email', 'role', 'telephone')}),
    )