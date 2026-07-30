import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cablaggio', '0004_progetto_logo_cliente'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipoCavo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, unique=True)),
                ('ordine', models.PositiveIntegerField(default=0)),
            ],
            options={'ordering': ['ordine', 'nome']},
        ),
        migrations.CreateModel(
            name='EsitoTest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=50, unique=True)),
                ('colore', models.CharField(
                    default='#22c55e', max_length=7,
                    help_text='Colore del badge nel report PDF, in formato esadecimale (es. #22c55e).',
                )),
                ('ordine', models.PositiveIntegerField(default=0)),
            ],
            options={'ordering': ['ordine', 'nome']},
        ),
        migrations.AddField(
            model_name='elementorack',
            name='unita_rack',
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text='Quante unità rack (U) occupa fisicamente questo pannello, per lo schema grafico.',
                verbose_name='Unità rack (U)',
            ),
        ),
        migrations.AddField(
            model_name='progetto',
            name='mostra_schema_rack',
            field=models.BooleanField(
                default=True,
                help_text='Se attivo, il report PDF include una pagina con lo schema grafico dei rack e dei pannelli.',
                verbose_name='Includi schema grafico rack nel PDF',
            ),
        ),
        migrations.AddField(
            model_name='posizione',
            name='tipo_cavo_fk',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='posizioni', to='cablaggio.tipocavo', verbose_name='Tipo cavo',
            ),
        ),
        migrations.AddField(
            model_name='posizione',
            name='esito_test_fk',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='posizioni', to='cablaggio.esitotest', verbose_name='Esito test',
            ),
        ),
    ]
