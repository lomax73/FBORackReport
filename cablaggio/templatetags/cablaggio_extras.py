from django import template

register = template.Library()


@register.filter
def porta_display(posizione, offset):
    return posizione.porta_display(offset)


@register.filter
def indirizzo_completo(cliente):
    """Indirizzo del cliente su una riga: 'Via X, CAP Città (PR)'."""
    if not cliente:
        return ''
    parti = [cliente.indirizzo]
    citta_cap = ' '.join(p for p in [cliente.cap, cliente.citta] if p)
    if citta_cap:
        parti.append(citta_cap)
    riga = ', '.join(p for p in parti if p)
    if cliente.provincia:
        riga = f'{riga} ({cliente.provincia})' if riga else f'({cliente.provincia})'
    return riga
