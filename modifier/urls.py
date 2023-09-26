from django.urls import path
from .views import add_inbound

urlpatterns = [
    path('add_inbound/', add_inbound, name='add_inbound'),
]
