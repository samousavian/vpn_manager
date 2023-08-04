from django.shortcuts import render
from datarefresher.models import Inbound
from datetime import datetime


def show_disabled_inbounds(request):
    # Query to filter Inbound objects with enable equal to 0
    disabled_inbounds = Inbound.objects.filter(enable=0)
    disabled_inbounds_edited = []
    
    # Get current UTC time
    now = datetime.utcnow()

    for inbound in disabled_inbounds:
        is_over_traffic = inbound.total < inbound.up + inbound.down
        traffic = (inbound.down + inbound.up) / 1073741824
        inbound.total = inbound.total / 1073741824
        inbound.up = inbound.up / 1073741824
        inbound.down = inbound.down / 1073741824

        server = inbound.server.name

        # Convert Unix timestamp to datetime object
        inbound.expiry_time = datetime.utcfromtimestamp(inbound.expiry_time / 1000)
        is_expired = inbound.expiry_time < now

        # Append to the list
        disabled_inbounds_edited.append((inbound, is_expired, is_over_traffic, traffic, server))
    # Pass the filtered objects to a template
    context = {'disabled_inbounds': disabled_inbounds_edited, 'now':now}
    return render(request, 'presenter/disabled_inbounds.html', context)
