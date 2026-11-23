from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('connexion/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('deconnexion/', auth_views.LogoutView.as_view(next_page='forum:dashboard'), name='logout'),
    path('inscription/', views.SignUpView.as_view(), name='register'),
    path('inscription/', views.SignUpView.as_view(), name='signup'),
    path('profil/', views.profile, name='profile'),
    path('profil/modifier/', views.profile_edit, name='profile-edit'),
    path('profil/modifier/', views.profile_edit, name='profile-update'),
    path('profil/supprimer/', views.delete_account, name='delete-account'),
    path('profil/supprimer/', views.delete_account, name='delete-user'),
    path('profil/<str:username>/', views.profile, name='profile-detail'),
]