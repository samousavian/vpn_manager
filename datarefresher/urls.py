from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('refresher-state/', views.refresher_state, name='refresher_state'),
]
