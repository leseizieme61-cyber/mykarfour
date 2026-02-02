from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Retourne dictionary[key] en gérant les cas où dictionary est None."""
    if not dictionary:
        return None
    try:
        # supporte dict.get et indexation
        if hasattr(dictionary, 'get'):
            return dictionary.get(key)
        return dictionary[key]
    except Exception:
        return None