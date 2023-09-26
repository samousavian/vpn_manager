from django.urls import path
from .views import all_inbounds, add_inbound, profile, login_view, logout_view

urlpatterns = [
    path('all_inbounds/', all_inbounds, name='all_inbounds'),
    # path('add_inbound/', add_inbound, name='add_inbound'),
    path('profile/<str:user_id>/', profile, name='profile'),
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]
