from airplay import Airplay
from django.http import Http404, HttpResponse

def device_discovery(request):
    return HttpResponse(','.join(Airplay().discovery()))

def image_serve(request, uid, device_idx):
    try:
        airplay = Airplay()
        airplay.discovery()
        airplay.send_image(uid, int(device_idx))
    except:
        raise Http404
    else:
        return HttpResponse(status=200)
