from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import TemplateView
from accounts.views import SignUpView, delete_account, profile, profile_edit
from accounts.admin import smart_admin_site

urlpatterns = [
    path('admin/', smart_admin_site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('comptes/', include('accounts.urls')),
    # ===== Modules (chaque membre décommente SA ligne) =====
    path('demandes/', include('demandes.urls')), # Module 1
    # path('marches/', include('marches.urls')),   # Module 2 - Molka
    path('incidents/', include('incidents.urls')), # Module 3 - Zaineb
    path('forum/', include('Forum_Events.urls')), # Module 4 - Nour
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='forum:dashboard'), name='logout'),
    path('accounts/signup/', SignUpView.as_view(), name='signup'),
    path('accounts/register/', SignUpView.as_view(), name='register'),
    path('accounts/profile/', profile, name='profile'),
    path('accounts/profile/edit/', profile_edit, name='profile-edit'),
    path('accounts/profile/delete/', delete_account, name='delete-account'),
    path('actualites/', include('actualites.urls')), # Module 5 - Ribel
    path('collecte/', include('agent_collect.urls')), # Module 6 - Mahmoud (Collecte)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
