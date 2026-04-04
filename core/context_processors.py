from .models import Region
from .utils import DEFAULT_WHATSAPP_TEMPLATE, get_current_region


def app_shell(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}

    return {
        'all_regions': Region.objects.order_by('name'),
        'current_region': get_current_region(request),
        'default_whatsapp_template': DEFAULT_WHATSAPP_TEMPLATE,
    }

