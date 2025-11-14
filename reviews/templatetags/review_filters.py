from django import template

register = template.Library()

@register.filter
def filter_by_rating(reviews, rating):
    """Filter reviews by rating"""
    return [r for r in reviews if r.rating == int(rating)]

@register.filter
def percentage(value, total):
    """Calculate percentage"""
    if total == 0:
        return 0
    return round((value / total) * 100, 1)