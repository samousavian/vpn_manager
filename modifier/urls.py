from django.urls import path
from .views import add_inbound, inbound_added

urlpatterns = [
    path('add_inbound/', add_inbound, name='add_inbound'),
    path('inbound_added/', inbound_added, name='inbound_added'),
]
