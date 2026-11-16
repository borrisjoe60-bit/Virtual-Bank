from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def read_notification(request):
    if request.method != 'POST':
        raise Http404()
    notification_id = request.POST.get('id')
    notification = Notification.objects.filter(user=request.user, pk=notification_id).first()
    if not notification:
        return JsonResponse({'status': 'failed', 'message': 'Notification not found.'}, status=404)
    notification.status = 'READ'
    notification.save(update_fields=['status'])
    return JsonResponse({'status': 'success'})
