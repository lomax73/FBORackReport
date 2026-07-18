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
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creato_il']

    def __str__(self):
        return self.nome


class Rack(models.Model):
    progetto = models.ForeignKey(Progetto, on_delete=models.CASCADE, related_name='rack_set')
    nome = models.CharField(max_length=255)
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
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordine', 'id']

    def __str__(self):
        return f'{self.get_tipo_display()} {self.etichetta}'

    def esito_riepilogo(self):
        """Conteggio posizioni per esito, per il riepilogo nel dettaglio progetto."""
        posizioni = list(self.posizioni.all())
        return {
            'ok': sum(1 for p in posizioni if p.esito_test == Posizione.ESITO_OK),
            'p2': sum(1 for p in posizioni if p.esito_test == Posizione.ESITO_P2),
            'non_cablate': sum(1 for p in posizioni if not p.cavo_n and not p.descrizione),
            'totale': len(posizioni),
        }


class Posizione(models.Model):
    ESITO_OK = 'ok'
    ESITO_P2 = 'p2'
    ESITO_CHOICES = [
        ('', '— non testato —'),
        (ESITO_OK, 'OK'),
        (ESITO_P2, 'P2'),
    ]

    elemento = models.ForeignKey(ElementoRack, on_delete=models.CASCADE, related_name='posizioni')
    numero = models.PositiveSmallIntegerField(help_text='Numero della posizione all\'interno del pannello (1..N).')
    cavo_n = models.CharField('N° cavo', max_length=50, blank=True)
    tipo_cavo = models.CharField('Tipo cavo', max_length=100, blank=True)
    descrizione = models.CharField(max_length=255, blank=True)
    posizione_in_campo = models.CharField(max_length=100, blank=True)
    esito_test = models.CharField(max_length=2, choices=ESITO_CHOICES, blank=True)

    class Meta:
        ordering = ['numero']
        unique_together = ['elemento', 'numero']

    def __str__(self):
        return f'{self.elemento} #{self.numero}'

    @property
    def non_cablata(self):
        return not self.cavo_n and not self.descrizione


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
