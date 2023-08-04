from django.urls import path
from .views import show_disabled_inbounds

urlpatterns = [
    path('disabled-inbounds/', show_disabled_inbounds, name='show_disabled_inbounds'),
]
