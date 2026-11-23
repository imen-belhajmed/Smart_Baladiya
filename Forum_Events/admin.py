from django.contrib import admin

from .models import Category, Comment, MemberProfile, Thread


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "allow_discussions", "allow_events", "updated_at")
    list_filter = ("allow_discussions", "allow_events")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "category", "author", "is_locked", "created_at")
    list_filter = ("kind", "category", "is_locked", "created_at")
    search_fields = ("title", "content", "category__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = (CommentInline,)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("thread", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "thread__title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "image")
    search_fields = ("user__username",)
