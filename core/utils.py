from datetime import date, timedelta

from .models import Region

DEFAULT_WHATSAPP_TEMPLATE = """Hare Krishna {name}

ISKCON Hare Krishna Movement Bhilai invites you to Vedic Science presentation level {level_no} on {date} Sunday at 10:30 am.

Venue
ISKCON Bhilai
Akshay Patra Foundation Campus
Sector 6
Bhilai
Location: https://maps.app.goo.gl/SAFyGnYdpB3bKgdMA"""

REGION_SESSION_KEY = 'current_region_id'


def get_current_region(request):
    region_id = request.session.get(REGION_SESSION_KEY)
    if not region_id:
        return None
    region = Region.objects.filter(pk=region_id).first()
    if region is None:
        request.session.pop(REGION_SESSION_KEY, None)
    return region


def apply_region_filter(queryset, request, field_name='region'):
    region = get_current_region(request)
    if not region:
        return queryset
    return queryset.filter(**{field_name: region})


def get_upcoming_sunday(from_date=None):
    from_date = from_date or date.today()
    days_until_sunday = (6 - from_date.weekday()) % 7
    return from_date + timedelta(days=days_until_sunday)


def get_level_no(session_type):
    return {
        'L1': '1',
        'L2': '2',
        'L3': '3',
    }.get(session_type, session_type)

