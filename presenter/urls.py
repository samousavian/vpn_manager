from django.urls import path
from .views import all_inbounds, add_inbound

urlpatterns = [
    path('all_inbounds/', all_inbounds, name='all_inbounds'),
    path('add_inbound/', add_inbound, name='add_inbound'),
]
