from io import BytesIO
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Category, Comment, MemberProfile, Thread


class ForumCrudTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="moderator",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(self.staff)

    def create_category(self, name="Community"):
        return Category.objects.create(name=name)

    def test_staff_can_create_update_and_delete_category(self):
        response = self.client.post(
            reverse("forum:category-create"),
            {
                "name": "Announcements",
                "description": "News from the municipality.",
                "allow_discussions": "on",
                "allow_events": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        category = Category.objects.get(name="Announcements")

        response = self.client.post(
            reverse("forum:category-update", args=[category.pk]),
            {
                "name": "Community News",
                "description": "Updated description.",
                "allow_discussions": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        category.refresh_from_db()
        self.assertEqual(category.name, "Community News")
        self.assertFalse(category.allow_events)

        response = self.client.post(
            reverse("forum:category-delete", args=[category.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_staff_can_manage_discussion_and_comments(self):
        category = self.create_category()
        response = self.client.post(
            reverse("forum:thread-create"),
            {
                "title": "Neighborhood meeting",
                "category": category.pk,
                "kind": Thread.Kind.DISCUSSION,
                "content": "What should we discuss?",
                "event_start": "",
                "event_end": "",
                "location": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        thread = Thread.objects.get(title="Neighborhood meeting")
        self.assertEqual(thread.author, self.staff)

        response = self.client.post(
            reverse("forum:comment-create", args=[thread.pk]),
            {"content": "I will attend."},
        )
        self.assertEqual(response.status_code, 302)
        comment = Comment.objects.get(thread=thread)
        self.assertEqual(comment.author, self.staff)

        response = self.client.post(
            reverse("forum:comment-update", args=[comment.pk]),
            {"content": "I will be there."},
        )
        self.assertEqual(response.status_code, 302)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "I will be there.")

        response = self.client.post(
            reverse("forum:comment-delete", args=[comment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())

        response = self.client.post(
            reverse("forum:thread-update", args=[thread.pk]),
            {
                "title": "Updated meeting",
                "category": category.pk,
                "kind": Thread.Kind.DISCUSSION,
                "content": "Updated agenda.",
                "event_start": "",
                "event_end": "",
                "location": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        thread.refresh_from_db()
        self.assertEqual(thread.title, "Updated meeting")
        self.assertEqual(
            self.client.get(
                reverse("forum:thread-detail", args=[thread.pk])
            ).status_code,
            200,
        )

        response = self.client.post(
            reverse("forum:thread-delete", args=[thread.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Thread.objects.filter(pk=thread.pk).exists())

    def test_events_require_a_start_time_and_appear_under_upcoming_events(self):
        category = self.create_category()
        url = reverse("forum:thread-create")
        invalid_response = self.client.post(
            url,
            {
                "title": "Clean-up day",
                "category": category.pk,
                "kind": Thread.Kind.EVENT,
                "content": "Join the clean-up.",
                "event_start": "",
                "event_end": "",
                "location": "Central park",
            },
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertFalse(Thread.objects.exists())

        response = self.client.post(
            url,
            {
                "title": "Clean-up day",
                "category": category.pk,
                "kind": Thread.Kind.EVENT,
                "content": "Join the clean-up.",
                "event_start": "2026-12-01T10:00",
                "event_end": "2026-12-01T12:00",
                "location": "Central park",
            },
        )
        self.assertEqual(response.status_code, 302)
        event = Thread.objects.get(title="Clean-up day")
        self.assertEqual(event.kind, Thread.Kind.EVENT)
        self.assertEqual(event.location, "Central park")
        self.assertEqual(
            self.client.get(reverse("forum:event-list")).status_code,
            200,
        )
        response = self.client.get(reverse("forum:thread-list"))
        self.assertContains(response, "Clean-up day")
        self.assertContains(response, "Central park")
        self.assertEqual(list(response.context["threads"]), [])
        self.assertContains(response, "Upcoming events")

    def test_thread_feed_shows_five_threads_per_category_and_category_page_shows_all(self):
        community = self.create_category()
        announcements = self.create_category("Announcements")
        community_threads = [
            Thread.objects.create(
                category=community,
                title=f"Community topic {index}",
                content="A discussion.",
            )
            for index in range(6)
        ]
        Thread.objects.create(
            category=announcements,
            title="Important update",
            content="An announcement.",
        )

        response = self.client.get(reverse("forum:thread-list"))

        community_preview = next(
            category
            for category in response.context["categories"]
            if category.pk == community.pk
        )
        self.assertEqual(len(community_preview.preview_threads), 5)
        self.assertContains(response, "Explore forums")
        self.assertContains(response, "Show latest 5 threads")

        response = self.client.get(
            reverse("forum:category-threads", args=[community.pk])
        )
        self.assertContains(response, community_threads[5].title)
        self.assertNotContains(response, "Important update")

    def test_discussion_search_matches_title_content_and_category(self):
        parks = self.create_category("Parks")
        community = self.create_category("Community")
        title_match = Thread.objects.create(
            category=community,
            title="Neighborhood meeting",
            content="Bring your questions.",
        )
        content_match = Thread.objects.create(
            category=community,
            title="Weekend plans",
            content="Let's meet at the garden.",
        )
        category_match = Thread.objects.create(
            category=parks,
            title="Trail cleanup",
            content="Help keep our paths clear.",
        )

        response = self.client.get(
            reverse("forum:thread-list"), {"q": "meeting"}
        )
        self.assertEqual(
            list(response.context["threads"]), [title_match]
        )
        self.assertContains(response, "Search results for")
        self.assertNotContains(response, "Weekend plans")

        response = self.client.get(
            reverse("forum:thread-list"), {"q": "garden"}
        )
        self.assertEqual(
            list(response.context["threads"]), [content_match]
        )

        response = self.client.get(
            reverse("forum:thread-list"), {"q": "Parks"}
        )
        self.assertEqual(
            list(response.context["threads"]), [category_match]
        )

    def test_upcoming_events_are_separate_from_discussions_and_categories(self):
        events_category = self.create_category("Events")
        other_category = self.create_category("Community")
        featured_event = Thread.objects.create(
            category=events_category,
            title="Featured event",
            content="Join us.",
            kind=Thread.Kind.EVENT,
            event_start=timezone.now(),
        )
        other_event = Thread.objects.create(
            category=other_category,
            title="Other event",
            content="Join us too.",
            kind=Thread.Kind.EVENT,
            event_start=timezone.now(),
        )

        response = self.client.get(reverse("forum:thread-list"))
        self.assertContains(response, "Featured event")
        self.assertContains(response, "Other event")
        self.assertContains(response, "Event image placeholder")
        page = response.content.decode()
        self.assertLess(
            page.index("Upcoming events"), page.index("Latest discussions")
        )
        self.assertEqual(list(response.context["threads"]), [])
        self.assertEqual(
            list(response.context["events"]), [featured_event, other_event]
        )
        self.assertNotIn(
            events_category.pk,
            [category.pk for category in response.context["categories"]],
        )

        dashboard_response = self.client.get(reverse("forum:dashboard"))
        self.assertContains(dashboard_response, "Featured event")
        self.assertContains(dashboard_response, "Upcoming events")

    def test_authenticated_users_can_comment_and_superusers_are_labeled_admin(self):
        category = self.create_category()
        thread = Thread.objects.create(
            category=category,
            title="Community topic",
            content="A discussion.",
        )
        regular_user = get_user_model().objects.create_user(
            username="neighbor",
            password="test-password",
        )
        self.client.force_login(regular_user)

        response = self.client.post(
            reverse("forum:comment-create", args=[thread.pk]),
            {"content": "A neighbor comment."},
        )

        self.assertRedirects(
            response, reverse("forum:thread-detail", args=[thread.pk])
        )
        self.assertEqual(Comment.objects.get(thread=thread).author, regular_user)

        admin = get_user_model().objects.create_superuser(
            username="siteadmin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin)
        self.client.post(
            reverse("forum:comment-create", args=[thread.pk]),
            {"content": "An administrator comment."},
        )

        response = self.client.get(reverse("forum:thread-detail", args=[thread.pk]))
        self.assertContains(response, "An administrator comment.")
        self.assertContains(response, "Admin")
        self.assertEqual(
            Comment.objects.get(content="An administrator comment.").author,
            admin,
        )

    def test_superuser_can_lock_threads_and_locked_threads_reject_comments(self):
        category = self.create_category()
        thread = Thread.objects.create(
            category=category,
            title="Locked topic",
            content="A discussion.",
        )
        admin = get_user_model().objects.create_superuser(
            username="siteadmin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin)
        lock_url = reverse("forum:thread-lock-toggle", args=[thread.pk])

        response = self.client.post(lock_url)

        self.assertRedirects(
            response, reverse("forum:thread-detail", args=[thread.pk])
        )
        thread.refresh_from_db()
        self.assertTrue(thread.is_locked)
        self.assertEqual(
            self.client.post(
                reverse("forum:comment-create", args=[thread.pk]),
                {"content": "This should be rejected."},
            ).status_code,
            302,
        )
        self.assertFalse(Comment.objects.filter(thread=thread).exists())
        response = self.client.get(reverse("forum:thread-detail", args=[thread.pk]))
        self.assertContains(response, "This thread is locked")
        self.assertNotContains(response, "Add comment")

        self.client.post(lock_url)
        thread.refresh_from_db()
        self.assertFalse(thread.is_locked)

    def test_category_with_threads_cannot_be_deleted(self):
        category = self.create_category()
        Thread.objects.create(
            category=category,
            title="Existing thread",
            content="Keep this content.",
        )

        response = self.client.post(
            reverse("forum:category-delete", args=[category.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(pk=category.pk).exists())

    def test_dashboard_and_category_pages_render(self):
        self.create_category()
        self.assertEqual(
            self.client.get(reverse("forum:dashboard")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("forum:category-list")).status_code,
            200,
        )

    def test_crud_pages_require_staff(self):
        self.client.logout()
        response = self.client.get(reverse("forum:category-create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)


class AuthenticationTests(TestCase):
    def test_signup_creates_and_logs_in_a_user(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "new-neighbor",
                "password1": "Blue-Horse-Tree-2026!",
                "password2": "Blue-Horse-Tree-2026!",
            },
        )

        self.assertRedirects(response, reverse("forum:dashboard"))
        user = get_user_model().objects.get(username="new-neighbor")
        self.assertEqual(
            str(self.client.session["_auth_user_id"]), str(user.pk)
        )
        response = self.client.get(reverse("forum:dashboard"))
        self.assertContains(response, "Sign out")
        self.assertNotContains(response, "Log in")
        self.assertNotContains(response, "Sign up")

    def test_navigation_shows_login_links_and_logout_is_post_only(self):
        user = get_user_model().objects.create_user(
            username="neighbor",
            password="Blue-Horse-Tree-2026!",
        )
        response = self.client.get(reverse("forum:dashboard"))
        self.assertContains(response, "Log in")
        self.assertContains(response, "Sign up")
        self.assertNotContains(response, "Sign out")

        response = self.client.post(
            reverse("login"),
            {"username": "neighbor", "password": "Blue-Horse-Tree-2026!"},
        )
        self.assertRedirects(response, reverse("forum:dashboard"))
        self.assertEqual(
            str(self.client.session["_auth_user_id"]), str(user.pk)
        )
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("forum:dashboard"))
        response = self.client.get(reverse("forum:dashboard"))
        self.assertContains(response, "Log in")
        self.assertNotContains(response, "Sign out")

    def test_profile_displays_members_threads_and_comments(self):
        member = get_user_model().objects.create_user(
            username="profile-member",
            password="test-password",
        )
        category = Category.objects.create(name="Community")
        thread = Thread.objects.create(
            category=category,
            author=member,
            title="Member thread",
            content="A profile activity test.",
        )
        Comment.objects.create(
            thread=thread,
            author=member,
            content="A profile comment.",
        )

        response = self.client.get(
            reverse("forum:profile", args=[member.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "profile-member")
        self.assertContains(response, "Member thread")
        self.assertContains(response, "A profile comment.")

    def test_only_superusers_can_access_django_admin(self):
        staff_user = get_user_model().objects.create_user(
            username="moderator",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 302)
        self.assertNotContains(
            self.client.get(reverse("forum:dashboard")), "Admin"
        )

        admin_user = get_user_model().objects.create_superuser(
            username="siteadmin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Site administration")


class ProfileImageTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(self.media_directory.cleanup)
        self.addCleanup(media_settings.disable)

    def image_upload(self, name="avatar.png"):
        image_bytes = BytesIO()
        Image.new("RGB", (4, 4), color="blue").save(image_bytes, format="PNG")
        return SimpleUploadedFile(
            name, image_bytes.getvalue(), content_type="image/png"
        )

    def test_member_can_upload_and_view_profile_image(self):
        member = get_user_model().objects.create_user(
            username="picture-member",
            password="test-password",
        )
        self.client.force_login(member)

        response = self.client.post(
            reverse("forum:profile-edit", args=[member.username]),
            {"image": self.image_upload()},
        )

        self.assertRedirects(
            response, reverse("forum:profile", args=[member.username])
        )
        profile = MemberProfile.objects.get(user=member)
        self.assertTrue(profile.image)
        self.assertTrue(profile.image.storage.exists(profile.image.name))
        response = self.client.get(
            reverse("forum:profile", args=[member.username])
        )
        self.assertContains(response, profile.image.url)

    def test_profile_image_upload_rejects_non_images_and_other_profiles(self):
        member = get_user_model().objects.create_user(
            username="picture-member",
            password="test-password",
        )
        other_member = get_user_model().objects.create_user(
            username="other-member",
            password="test-password",
        )
        self.client.force_login(member)

        response = self.client.post(
            reverse("forum:profile-edit", args=[member.username]),
            {
                "image": SimpleUploadedFile(
                    "not-an-image.png", b"invalid image data", content_type="image/png"
                )
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MemberProfile.objects.get(user=member).image)
        self.assertEqual(
            self.client.get(
                reverse("forum:profile-edit", args=[other_member.username])
            ).status_code,
            404,
        )
