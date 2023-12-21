from django.urls import path
from .views import *

urlpatterns = [
    path('add_inbound/', add_inbound, name='add_inbound'),
    path('inbound_added/', inbound_added, name='inbound_added'),
    path('update_inbound/<str:user_id>/<str:remark>/<str:server_name>/<str:pre_traffic>/', update_inbound, name='update_inbound'),
    path('inbound_updated/', inbound_updated, name='inbound_updated'),
]
