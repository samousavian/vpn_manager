from django.urls import path
from . import views

urlpatterns = [
    path('', views.refresher_db, name='refresher_db'),
    path('refresher-state/', views.refresher_state, name='refresher_state'),
]
