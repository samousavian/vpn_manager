from django.urls import path
from . import views

urlpatterns = [
    path('inbounds-update/', views.xui, name='inbounds_update'),
]
