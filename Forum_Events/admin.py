from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin

from .models import Category, Comment, MemberProfile, Thread


class SuperuserAdminSite(admin.AdminSite):
    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser


superuser_admin_site = SuperuserAdminSite(name="admin")
superuser_admin_site.register(get_user_model(), UserAdmin)
superuser_admin_site.register(Group, GroupAdmin)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Category, site=superuser_admin_site)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "allow_discussions", "allow_events", "updated_at")
    list_filter = ("allow_discussions", "allow_events")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Thread, site=superuser_admin_site)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "category", "author", "is_locked", "created_at")
    list_filter = ("kind", "category", "is_locked", "created_at")
    search_fields = ("title", "content", "category__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = (CommentInline,)


@admin.register(Comment, site=superuser_admin_site)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("thread", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "thread__title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MemberProfile, site=superuser_admin_site)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "image")
    search_fields = ("user__username",)
