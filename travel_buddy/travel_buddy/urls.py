from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users import views as users_views  # ← ДОБАВИТЬ

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('routes.urls')),
    path('users/', include('users.urls')),
    path('responses/', include('responses.urls')),
    path('reviews/', include('reviews.urls')),
    path('chat/', include('chat.urls')),
    path('login/', users_views.user_login, name='login'),  # ← ИСПОЛЬЗУЕМ ВАШУ ФУНКЦИЮ
    path('logout/', users_views.user_logout, name='logout'),  # ← ИСПОЛЬЗУЕМ ВАШУ ФУНКЦИЮ
    path('complaints/', include('complaints.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)