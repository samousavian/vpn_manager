from django.urls import path
from .views import all_inbounds, add_inbound, profile, login_view, logout_view

urlpatterns = [
    path('profile/<str:server_name>/<str:email>/', profile, name='profile'),


    path('all_inbounds/', all_inbounds, name='all_inbounds'),
    # path('add_inbound/', add_inbound, name='add_inbound'),
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]
