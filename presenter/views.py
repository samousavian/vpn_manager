from django.shortcuts import render
from datarefresher.models import Inbound
from datetime import datetime
from datarefresher.views import inbounds_all as inbounds_all

def show_disabled_inbounds(request):
    now = datetime.utcnow()
    df_all_inbounds = inbounds_all(request)

    df_all_inbounds['is_over_traffic'] = df_all_inbounds.apply(lambda row: row['total'] < (row['up'] + row['down']), axis=1)
    df_all_inbounds['traffic'] = df_all_inbounds.apply(lambda row: (row['up'] + row['down']) / 1073741824 , axis=1)
    df_all_inbounds['total'] = df_all_inbounds.apply(lambda row: row['total'] / 1073741824 , axis=1)
    df_all_inbounds['up'] = df_all_inbounds.apply(lambda row: row['up'] / 1073741824 , axis=1)
    df_all_inbounds['down'] = df_all_inbounds.apply(lambda row: row['down'] / 1073741824 , axis=1)
    df_all_inbounds['expiry_time'] = df_all_inbounds.apply(lambda row: datetime.utcfromtimestamp(row['expiryTime'] / 1000) , axis=1)
    df_all_inbounds['is_expired'] = df_all_inbounds.apply(lambda row: row['expiry_time'] < now, axis=1)
    
    df_disabled_inbounds =  df_all_inbounds[df_all_inbounds['enable'] == False]
    df_enabled_inbounds =  df_all_inbounds[df_all_inbounds['enable'] == True]
    
    all_inbounds = df_all_inbounds.to_dict(orient='records')
    disabled_inbounds = df_disabled_inbounds.to_dict(orient='records')
    enabled_inbounds = df_enabled_inbounds.to_dict(orient='records')

    # Pass the filtered objects to a template   
    context = {'disabled_inbounds': disabled_inbounds, 'enabled_inbounds': enabled_inbounds, 'all_inbounds': all_inbounds, 'now':now}
    return render(request, 'presenter/all_inbounds.html', context)

