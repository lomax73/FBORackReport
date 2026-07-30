from django.db import migrations


def migra_dati(apps, schema_editor):
    Posizione = apps.get_model('cablaggio', 'Posizione')
    TipoCavo = apps.get_model('cablaggio', 'TipoCavo')
    EsitoTest = apps.get_model('cablaggio', 'EsitoTest')

    ok, _ = EsitoTest.objects.get_or_create(nome='OK', defaults={'colore': '#22c55e', 'ordine': 0})
    p2, _ = EsitoTest.objects.get_or_create(nome='P2', defaults={'colore': '#f59e0b', 'ordine': 1})
    mappa_esito = {'ok': ok, 'p2': p2}

    cache_tipo_cavo = {}
    for posizione in Posizione.objects.all():
        aggiornato = False
        valore_tipo_cavo = (posizione.tipo_cavo or '').strip()
        if valore_tipo_cavo:
            tipo_cavo = cache_tipo_cavo.get(valore_tipo_cavo)
            if tipo_cavo is None:
                tipo_cavo, _ = TipoCavo.objects.get_or_create(
                    nome=valore_tipo_cavo, defaults={'ordine': len(cache_tipo_cavo)}
                )
                cache_tipo_cavo[valore_tipo_cavo] = tipo_cavo
            posizione.tipo_cavo_fk = tipo_cavo
            aggiornato = True
        if posizione.esito_test in mappa_esito:
            posizione.esito_test_fk = mappa_esito[posizione.esito_test]
            aggiornato = True
        if aggiornato:
            posizione.save(update_fields=['tipo_cavo_fk', 'esito_test_fk'])


def rimuovi_dati(apps, schema_editor):
    # Nessun rollback: i valori tornerebbero comunque nei vecchi campi
    # CharField ancora presenti finché non viene rimossa la migrazione 0007.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cablaggio', '0005_aggiungi_config_e_unita_rack'),
    ]

    operations = [
        migrations.RunPython(migra_dati, rimuovi_dati),
    ]
