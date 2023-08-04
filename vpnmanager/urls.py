from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('data/', include('datarefresher.urls')),
    path('presenter/', include('presenter.urls')),
]
