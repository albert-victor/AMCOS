from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.core.views import welcome, health_check, database_status_api

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health'),
    path('system/health/', health_check, name='system_health'),
    path('system/status/', database_status_api, name='system_status_api'),
    path('', welcome, name='home'),
    path('auth/', include('apps.authentication.urls')),
    path('dashboard/', include(('apps.core.urls', 'core'), namespace='core')),
    path('cooperative/', include('apps.cooperative.urls')),
    path('members/', include('apps.members.urls')),
    path('payments/', include('apps.payments.urls')),
    path('savings/', include('apps.savings.urls')),
    path('shares/', include('apps.shares.urls')),
    path('loans/', include('apps.loans.urls')),
    path('accounting/', include('apps.accounting.urls')),
    path('governance/', include('apps.governance.urls')),
    path('reports/', include('apps.reporting.urls')),
    path('audit/', include('apps.audit.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('chatbot/', include('chatbot.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
