from django.urls import path
from .views import *

urlpatterns = [
    path('update-client/<str:user_id>/<str:remark>/<str:server_name>/<str:pre_traffic>/<str:expiry_time>/<str:total_used>/', update_client, name='update_client'),
    path('updated-client/', inbound_updated, name='inbound_updated'),

    path('add-client/', add_inbound, name='add_inbound'),
    path('added-client/', inbound_added, name='inbound_added'),
]
