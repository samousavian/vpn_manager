from django.urls import path
from .views import all_clients, profile, login_view, logout_view

urlpatterns = [
    path('profile/<str:server_name>/<str:email>/', profile, name='profile'),
    path('all-clients/', all_clients, name='all_clients'),
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]
