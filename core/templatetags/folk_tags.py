from django import template

register = template.Library()


@register.filter
def wa_number(phone):
    """
    Convert any Indian phone number format to WhatsApp-ready 12-digit string.
    Examples:
      8999145848        → 918999145848
      +91 8999145848    → 918999145848
      91-8999-145848    → 918999145848
      08999145848       → 918999145848
    """
    digits = ''.join(c for c in str(phone) if c.isdigit())
    if len(digits) == 10:
        return '91' + digits
    if len(digits) == 11 and digits.startswith('0'):
        return '91' + digits[1:]
    if len(digits) == 12 and digits.startswith('91'):
        return digits
    # fallback: take last 10 digits and prepend 91
    return '91' + digits[-10:] if len(digits) >= 10 else digits
