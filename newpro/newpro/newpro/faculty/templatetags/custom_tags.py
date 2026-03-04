from django import template
register = template.Library()

@register.filter
def to(start, end):
    """Generate a range of numbers inclusive."""
    return range(start, end + 1)

@register.filter
def get_item(dictionary, key):
    """Retrieve an item from a dictionary by key."""
    return dictionary.get(key)

@register.filter
def make_key(value, arg):
    """Combine two values (like day + period) into a tuple key."""
    return (value, arg)

@register.filter
def zip_lists(a, b):
    """Zip two lists together."""
    return zip(a, b)
