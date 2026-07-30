from django.db import models


class Progetto(models.Model):
    """Un intervento di cablaggio strutturato presso un cliente, che
    produce un report PDF con uno o più rack testati.

    cliente_id fa riferimento all'anagrafica condivisa nel Portale FBO
    (clienti/api/internal/): nessuna FK cross-database, si risolve a
    runtime via portal_client.py (vedi memoria
    project-multi-app-portal-architecture)."""

    nome = models.CharField(max_length=255)
    cliente_id = models.UUIDField(
        help_text="Riferimento al cliente nell'anagrafica condivisa del Portale.",
    )
    sito = models.CharField(
        'Sito / cliente finale', max_length=255, blank=True,
        help_text='Es. "SHOP Prada Vienna Ground Floor": può essere diverso dal cliente in anagrafica.',
    )
    data_intervento = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    logo_cliente = models.ImageField(
        'Logo cliente', upload_to='loghi_cliente/%Y/%m/', blank=True, null=True,
        help_text='Mostrato in testa alla scheda progetto e nella prima pagina del report PDF.',
    )
    mostra_schema_rack = models.BooleanField(
        'Includi schema grafico rack nel PDF', default=True,
        help_text='Se attivo, il report PDF include una pagina con lo schema grafico dei rack e dei pannelli.',
    )
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creato_il']

    def __str__(self):
        return self.nome


class Rack(models.Model):
    progetto = models.ForeignKey(Progetto, on_delete=models.CASCADE, related_name='rack_set')
    nome = models.CharField(max_length=255)
    posizione = models.CharField(
        max_length=255, blank=True,
        help_text='Dove si trova fisicamente il rack, es. "Sala CED, piano terra".',
    )
    note = models.CharField(max_length=255, blank=True)
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordine', 'id']

    def __str__(self):
        return self.nome


class ElementoRack(models.Model):
    TIPO_PATCH_PANEL = 'patch_panel'
    TIPO_CASSETTO_FIBRA = 'cassetto_fibra'
    TIPO_CHOICES = [
        (TIPO_PATCH_PANEL, 'Patch panel'),
        (TIPO_CASSETTO_FIBRA, 'Cassetto fibra'),
    ]
    DIMENSIONE_CHOICES = [
        (8, '8 posizioni'),
        (12, '12 posizioni'),
        (16, '16 posizioni'),
        (24, '24 posizioni'),
    ]

    rack = models.ForeignKey(Rack, on_delete=models.CASCADE, related_name='elementi')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    etichetta = models.CharField('Etichetta', max_length=10, help_text='Es. "A", "B", "C".')
    n_posizioni = models.PositiveSmallIntegerField('Posizioni', choices=DIMENSIONE_CHOICES)
    unita_rack = models.PositiveSmallIntegerField(
        'Unità rack (U)', default=1,
        help_text='Quante unità rack (U) occupa fisicamente questo pannello, per lo schema grafico.',
    )
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordine', 'id']

    def __str__(self):
        return f'{self.get_tipo_display()} {self.etichetta}'

    def esito_riepilogo(self):
        """Conteggio posizioni per esito (con relativo colore) e non cablate,
        per il riepilogo nel dettaglio progetto."""
        posizioni = list(self.posizioni.all())
        conteggi = {}
        for p in posizioni:
            if p.esito_test:
                conteggi[p.esito_test] = conteggi.get(p.esito_test, 0) + 1
        return {
            'per_esito': [
                {'esito': esito, 'conteggio': conteggio}
                for esito, conteggio in sorted(conteggi.items(), key=lambda kv: (kv[0].ordine, kv[0].nome))
            ],
            'non_cablate': sum(1 for p in posizioni if not p.cavo_n and not p.descrizione),
            'totale': len(posizioni),
        }


class TipoCavo(models.Model):
    """Voce configurabile per il menu a discesa 'Tipo cavo' (pagina di
    configurazione)."""

    nome = models.CharField(max_length=100, unique=True)
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordine', 'nome']

    def __str__(self):
        return self.nome


class EsitoTest(models.Model):
    """Voce configurabile per il menu a discesa 'Esito test' (pagina di
    configurazione), con un colore per il badge nel report PDF."""

    nome = models.CharField(max_length=50, unique=True)
    colore = models.CharField(
        max_length=7, default='#22c55e',
        help_text='Colore del badge nel report PDF, in formato esadecimale (es. #22c55e).',
    )
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordine', 'nome']

    def __str__(self):
        return self.nome


class Posizione(models.Model):
    elemento = models.ForeignKey(ElementoRack, on_delete=models.CASCADE, related_name='posizioni')
    numero = models.PositiveSmallIntegerField(help_text='Numero della posizione all\'interno del pannello (1..N).')
    porta_label = models.CharField(
        'Porta', max_length=20, blank=True,
        help_text=(
            "Sovrascrive il numero di porta calcolato automaticamente. "
            "Usato per i cassetti fibra, dove la numerazione fisica delle "
            "porte spesso non è progressiva come nei patch panel."
        ),
    )
    cavo_n = models.CharField('N° cavo', max_length=50, blank=True)
    tipo_cavo = models.ForeignKey(
        TipoCavo, verbose_name='Tipo cavo', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='posizioni',
    )
    descrizione = models.CharField(max_length=255, blank=True)
    posizione_in_campo = models.CharField(max_length=100, blank=True)
    esito_test = models.ForeignKey(
        EsitoTest, verbose_name='Esito test', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='posizioni',
    )

    class Meta:
        ordering = ['numero']
        unique_together = ['elemento', 'numero']

    def __str__(self):
        return f'{self.elemento} #{self.numero}'

    @property
    def non_cablata(self):
        return not self.cavo_n and not self.descrizione

    def porta_display(self, offset=0):
        """Numero di porta da mostrare: porta_label se impostata
        manualmente (cassetti fibra), altrimenti il progressivo calcolato."""
        return self.porta_label or str(offset + self.numero)


class RackAllegato(models.Model):
    """Report scaricati dagli strumenti di verifica (es. export FLUKE),
    allegati liberamente a un rack."""

    rack = models.ForeignKey(Rack, on_delete=models.CASCADE, related_name='allegati')
    file = models.FileField(upload_to='rackreport_allegati/%Y/%m/')
    nome_originale = models.CharField(max_length=255, blank=True)
    caricato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-caricato_il']

    def __str__(self):
        return self.nome_originale or self.file.name
