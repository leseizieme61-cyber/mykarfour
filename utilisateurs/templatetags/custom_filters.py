from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permet d'accéder à un élément de dictionnaire par sa clé dans un template."""
    if dictionary and key in dictionary:
        return dictionary.get(key)
    return ''
