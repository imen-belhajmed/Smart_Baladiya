from django.contrib import admin

from accounts.admin import smart_admin_site

from .models import Category, Comment, MemberProfile, Thread, ThreadMedia


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class ThreadMediaInline(admin.TabularInline):
    model = ThreadMedia
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Category, site=smart_admin_site)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "allow_discussions", "allow_events", "updated_at")
    list_filter = ("allow_discussions", "allow_events")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Thread, site=smart_admin_site)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "category", "author", "is_locked", "created_at")
    list_filter = ("kind", "category", "is_locked", "created_at")
    search_fields = ("title", "content", "category__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = (CommentInline, ThreadMediaInline)


@admin.register(Comment, site=smart_admin_site)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("thread", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "thread__title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MemberProfile, site=smart_admin_site)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "image")
    search_fields = ("user__username",)


@admin.register(ThreadMedia, site=smart_admin_site)
class ThreadMediaAdmin(admin.ModelAdmin):
    list_display = ("thread", "kind", "caption", "uploaded_by", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("thread__title", "caption", "uploaded_by__username")
    readonly_fields = ("created_at",)
