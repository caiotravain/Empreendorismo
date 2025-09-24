from django import template

register = template.Library()

@register.filter
def split(value, delimiter):
    """
    Split a string by delimiter and return a list.
    Usage: {{ "a,b,c"|split:"," }}
    """
    if value and delimiter:
        return value.split(delimiter)
    return []
