from django import template

register = template.Library()


@register.filter
def porta_display(posizione, offset):
    return posizione.porta_display(offset)
