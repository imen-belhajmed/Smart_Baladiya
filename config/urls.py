from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('comptes/', include('accounts.urls')),
    # ===== Modules (chaque membre décommente SA ligne) =====
    path('demandes/', include('demandes.urls')), # Module 1
    # path('marches/', include('marches.urls')),   # Module 2 - Molka
    # path('incidents/', include('incidents.urls')), # Module 3 - Zaineb
    # path('forum/', include('forum.urls')),     # Module 4 - Nour
    path('actualites/', include('actualites.urls')), # Module 5 - Ribel
    # path('dechets/', include('dechets.urls')),   # Module 6 - Mahmoud
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
