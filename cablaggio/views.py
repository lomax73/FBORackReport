import io
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.text import slugify
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from pypdf import PdfReader, PdfWriter
from weasyprint import HTML
from weasyprint import default_url_fetcher

from . import portal_client
from .forms import (
    ElementoRackForm,
    EsitoTestFormSet,
    PosizioneFormSet,
    ProgettoForm,
    RackForm,
    TipoCavoFormSet,
)
from .models import ElementoRack, EsitoTest, Posizione, Progetto, Rack, RackAllegato, TipoCavo


@dataclass
class ClienteInfo:
    """Dati del cliente risolti dall'anagrafica condivisa nel Portale."""

    id: str = ''
    ragione_sociale: str = ''
    indirizzo: str = ''
    cap: str = ''
    citta: str = ''
    provincia: str = ''
    piva: str = ''
    email: str = ''
    telefono: str = ''
    note: str = ''

    def __str__(self):
        return self.ragione_sociale


def _attach_clienti(progetti):
    """Risolve cliente_id -> dati cliente per una lista di progetti con UNA
    sola chiamata al Portale (non una per riga). Se il Portale non risponde
    o il cliente non esiste più, fallback esplicito invece di un errore."""
    progetti = list(progetti)
    try:
        by_id = {c['id']: c for c in portal_client.list_clienti()}
    except portal_client.PortalUnavailableError:
        by_id = {}
    for progetto in progetti:
        dati = by_id.get(str(progetto.cliente_id))
        progetto.cliente = ClienteInfo(**dati) if dati else ClienteInfo(ragione_sociale='Cliente non disponibile')
    return progetti


def sync_posizioni(elemento):
    """Crea/rimuove le Posizione di un elemento per allinearle a n_posizioni."""
    esistenti = {p.numero: p for p in elemento.posizioni.all()}
    for numero in range(1, elemento.n_posizioni + 1):
        if numero not in esistenti:
            Posizione.objects.create(elemento=elemento, numero=numero)
    for numero, posizione in esistenti.items():
        if numero > elemento.n_posizioni:
            posizione.delete()


def elementi_con_offset(rack):
    """Elementi del rack con il numero di porta assoluto di partenza
    (numerazione continua nel rack, es. pannello B parte da 25 se A ne ha 24)."""
    offset = 0
    risultato = []
    for elemento in rack.elementi.all():
        risultato.append((elemento, offset))
        offset += elemento.n_posizioni
    return risultato


# --- Progetto -----------------------------------------------------------

class ProgettoListView(LoginRequiredMixin, ListView):
    model = Progetto
    template_name = 'cablaggio/progetto_list.html'
    context_object_name = 'progetti'

    def get_queryset(self):
        return _attach_clienti(super().get_queryset())


class ProgettoDetailView(LoginRequiredMixin, DetailView):
    model = Progetto
    template_name = 'cablaggio/progetto_detail.html'
    context_object_name = 'progetto'

    def get_object(self, queryset=None):
        progetto = super().get_object(queryset)
        _attach_clienti([progetto])
        return progetto

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rack_list = []
        for rack in self.object.rack_set.prefetch_related('elementi__posizioni', 'allegati'):
            rack_list.append({
                'rack': rack,
                'elementi': [
                    {'elemento': elemento, 'offset': offset, 'riepilogo': elemento.esito_riepilogo()}
                    for elemento, offset in elementi_con_offset(rack)
                ],
            })
        context['rack_list'] = rack_list
        return context


class ProgettoCreateView(LoginRequiredMixin, CreateView):
    model = Progetto
    form_class = ProgettoForm
    template_name = 'cablaggio/progetto_form.html'

    def get_success_url(self):
        return reverse('progetto-detail', args=[self.object.pk])


class ProgettoUpdateView(LoginRequiredMixin, UpdateView):
    model = Progetto
    form_class = ProgettoForm
    template_name = 'cablaggio/progetto_form.html'

    def get_success_url(self):
        return reverse('progetto-detail', args=[self.object.pk])


class ProgettoDeleteView(LoginRequiredMixin, DeleteView):
    model = Progetto
    template_name = 'cablaggio/progetto_confirm_delete.html'
    success_url = reverse_lazy('progetto-list')

    def get_object(self, queryset=None):
        progetto = super().get_object(queryset)
        _attach_clienti([progetto])
        return progetto


# --- Rack -----------------------------------------------------------------

class RackCreateView(LoginRequiredMixin, CreateView):
    model = Rack
    form_class = RackForm
    template_name = 'cablaggio/rack_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.progetto = get_object_or_404(Progetto, pk=kwargs['progetto_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['progetto'] = self.progetto
        context['progetto_id'] = self.progetto.pk
        return context

    def form_valid(self, form):
        form.instance.progetto = self.progetto
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('progetto-detail', args=[self.progetto.pk])


class RackUpdateView(LoginRequiredMixin, UpdateView):
    model = Rack
    form_class = RackForm
    template_name = 'cablaggio/rack_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['progetto_id'] = self.object.progetto_id
        return context

    def get_success_url(self):
        return reverse('progetto-detail', args=[self.object.progetto_id])


class RackDeleteView(LoginRequiredMixin, DeleteView):
    model = Rack
    template_name = 'cablaggio/rack_confirm_delete.html'

    def get_success_url(self):
        return reverse('progetto-detail', args=[self.object.progetto_id])


# --- ElementoRack -----------------------------------------------------------

class ElementoRackCreateView(LoginRequiredMixin, CreateView):
    model = ElementoRack
    form_class = ElementoRackForm
    template_name = 'cablaggio/elemento_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.rack = get_object_or_404(Rack, pk=kwargs['rack_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rack'] = self.rack
        context['progetto_id'] = self.rack.progetto_id
        return context

    def form_valid(self, form):
        form.instance.rack = self.rack
        response = super().form_valid(form)
        sync_posizioni(self.object)
        return response

    def get_success_url(self):
        return reverse('elemento-posizioni', args=[self.object.pk])


class ElementoRackUpdateView(LoginRequiredMixin, UpdateView):
    model = ElementoRack
    form_class = ElementoRackForm
    template_name = 'cablaggio/elemento_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['progetto_id'] = self.object.rack.progetto_id
        return context

    def post(self, request, *args, **kwargs):
        # self.object viene mutato dal binding del ModelForm (form.instance è
        # self.object) già durante form.is_valid(), prima di form_valid(): va
        # letto il valore precedente dal DB qui, non da self.object più sotto.
        self.object = self.get_object()
        self._n_posizioni_precedente = self.object.n_posizioni
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        nuovo_n = form.cleaned_data['n_posizioni']
        if nuovo_n < self._n_posizioni_precedente:
            da_rimuovere = self.object.posizioni.filter(numero__gt=nuovo_n)
            non_vuote = [p for p in da_rimuovere if p.cavo_n or p.descrizione]
            if non_vuote and self.request.POST.get('conferma_riduzione') != '1':
                messages.error(
                    self.request,
                    f'Riducendo a {nuovo_n} posizioni perderai i dati di {len(non_vuote)} '
                    'posizioni già compilate. Conferma per procedere.',
                )
                return self.render_to_response(
                    self.get_context_data(form=form, richiedi_conferma_riduzione=True)
                )
        response = super().form_valid(form)
        sync_posizioni(self.object)
        return response

    def get_success_url(self):
        return reverse('progetto-detail', args=[self.object.rack.progetto_id])


class ElementoRackDeleteView(LoginRequiredMixin, DeleteView):
    model = ElementoRack
    template_name = 'cablaggio/elemento_confirm_delete.html'

    def get_success_url(self):
        return reverse('progetto-detail', args=[self.object.rack.progetto_id])


def _etichetta_duplicata(rack, etichetta):
    """Etichetta libera per un pannello duplicato: la lettera successiva se
    l'originale è una singola lettera, altrimenti 'etichetta copia'."""
    esistenti = set(rack.elementi.values_list('etichetta', flat=True))
    if len(etichetta) == 1 and etichetta.isalpha():
        codice = ord(etichetta.upper())
        while codice < ord('Z'):
            codice += 1
            candidata = chr(codice)
            if candidata not in esistenti:
                return candidata
    base = f'{etichetta} copia'
    candidata = base
    n = 2
    while candidata in esistenti:
        candidata = f'{base} {n}'
        n += 1
    return candidata[:10]


@login_required
def elemento_duplica(request, pk):
    if request.method != 'POST':
        return redirect('progetto-detail', pk=get_object_or_404(ElementoRack, pk=pk).rack.progetto_id)
    originale = get_object_or_404(ElementoRack, pk=pk)
    duplicato = ElementoRack.objects.create(
        rack=originale.rack,
        tipo=originale.tipo,
        etichetta=_etichetta_duplicata(originale.rack, originale.etichetta),
        n_posizioni=originale.n_posizioni,
        unita_rack=originale.unita_rack,
        ordine=originale.ordine,
    )
    sync_posizioni(duplicato)
    messages.success(request, f'Pannello "{duplicato.etichetta}" creato come copia di "{originale.etichetta}".')
    return redirect('progetto-detail', pk=originale.rack.progetto_id)


@login_required
def elemento_posizioni(request, pk):
    elemento = get_object_or_404(ElementoRack, pk=pk)
    if request.method == 'POST':
        formset = PosizioneFormSet(request.POST, instance=elemento)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Posizioni aggiornate.')
            return redirect('progetto-detail', pk=elemento.rack.progetto_id)
    else:
        formset = PosizioneFormSet(instance=elemento)

    offset = dict(elementi_con_offset(elemento.rack)).get(elemento, 0)
    return render(request, 'cablaggio/posizioni_form.html', {
        'elemento': elemento,
        'formset': formset,
        'offset': offset,
        'tipi_cavo': TipoCavo.objects.all(),
        'esiti_test': EsitoTest.objects.all(),
    })


# --- Configurazione -------------------------------------------------------

@login_required
def configurazione(request):
    if request.method == 'POST':
        tipo_formset = TipoCavoFormSet(request.POST, prefix='tipocavo', queryset=TipoCavo.objects.all())
        esito_formset = EsitoTestFormSet(request.POST, prefix='esitotest', queryset=EsitoTest.objects.all())
        if tipo_formset.is_valid() and esito_formset.is_valid():
            tipo_formset.save()
            esito_formset.save()
            messages.success(request, 'Configurazione aggiornata.')
            return redirect('configurazione')
    else:
        tipo_formset = TipoCavoFormSet(prefix='tipocavo', queryset=TipoCavo.objects.all())
        esito_formset = EsitoTestFormSet(prefix='esitotest', queryset=EsitoTest.objects.all())
    return render(request, 'cablaggio/configurazione.html', {
        'tipo_formset': tipo_formset,
        'esito_formset': esito_formset,
    })


# --- Allegati -----------------------------------------------------------

@login_required
def rack_allegato_upload(request, pk):
    rack = get_object_or_404(Rack, pk=pk)
    if request.method == 'POST':
        files = request.FILES.getlist('file')
        if not files:
            messages.error(request, 'Seleziona almeno un file da caricare.')
        else:
            for f in files:
                RackAllegato.objects.create(rack=rack, file=f, nome_originale=f.name)
            messages.success(request, f'{len(files)} file caricat{"o" if len(files) == 1 else "i"}.')
    return redirect('progetto-detail', pk=rack.progetto_id)


class RackAllegatoDeleteView(LoginRequiredMixin, DeleteView):
    model = RackAllegato
    template_name = 'cablaggio/allegato_confirm_delete.html'

    def get_success_url(self):
        return reverse('progetto-detail', args=[self.object.rack.progetto_id])


# --- Report PDF -----------------------------------------------------------

PANNELLI_PER_PAGINA = 2


def _righe_rack(rack):
    """Sequenza dei pannelli di un rack (con il titolo da mostrare sopra),
    con 2 pannelli per pagina: il titolo va ripetuto se una pagina inizia
    a metà del rack."""
    elementi = elementi_con_offset(rack)
    righe = [
        {'elemento': elemento, 'offset': offset, 'nuovo_rack': indice == 0}
        for indice, (elemento, offset) in enumerate(elementi)
    ]
    for i, riga in enumerate(righe):
        inizio_pagina = i > 0 and i % PANNELLI_PER_PAGINA == 0
        riga['spezza_pagina_prima'] = inizio_pagina
        riga['mostra_titolo_rack'] = riga['nuovo_rack'] or inizio_pagina
    return righe


def _fetcher_file_locali(url):
    """Legge direttamente dal disco le immagini servite da /media/ e
    /static/ invece di richiederle in HTTPS: sullo stesso VPS il
    certificato è self-signed e il fetcher HTTPS di default di
    WeasyPrint le scarta senza errore visibile (l'immagine sparisce e
    resta il solo alt text)."""
    path = urlparse(url).path
    for url_prefix, radice in (
        (f'/{settings.MEDIA_URL.strip("/")}/', settings.MEDIA_ROOT),
        (f'/{settings.STATIC_URL.strip("/")}/', settings.STATIC_ROOT),
    ):
        if radice and path.startswith(url_prefix):
            file_path = Path(radice) / path[len(url_prefix):]
            if file_path.is_file():
                mime_type, _ = mimetypes.guess_type(str(file_path))
                return {
                    'mime_type': mime_type or 'application/octet-stream',
                    'file_obj': open(file_path, 'rb'),
                }
    return default_url_fetcher(url)


def _pdf_da_html(template_name, contesto, request):
    html_string = render_to_string(template_name, contesto)
    return HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/'),
        url_fetcher=_fetcher_file_locali,
    ).write_pdf()


def _unisci_pdf(blocchi):
    """Concatena in un unico PDF una lista di documenti PDF completi (bytes)."""
    writer = PdfWriter()
    for blocco in blocchi:
        for pagina in PdfReader(io.BytesIO(blocco)).pages:
            writer.add_page(pagina)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@login_required
def progetto_report_pdf(request, pk):
    progetto = get_object_or_404(Progetto, pk=pk)
    _attach_clienti([progetto])

    blocchi = [_pdf_da_html('cablaggio/report_pdf_intro.html', {
        'progetto': progetto,
        'now': timezone.localtime(),
    }, request)]

    if progetto.mostra_schema_rack:
        blocchi.append(_pdf_da_html('cablaggio/report_pdf_schema.html', {
            'progetto': progetto,
        }, request))

    for rack in progetto.rack_set.prefetch_related('elementi__posizioni', 'allegati'):
        allegati_pdf = [a for a in rack.allegati.all() if a.file.name.lower().endswith('.pdf')]
        allegati_non_pdf = [a for a in rack.allegati.all() if not a.file.name.lower().endswith('.pdf')]
        blocchi.append(_pdf_da_html('cablaggio/report_pdf_rack.html', {
            'progetto': progetto,
            'rack': rack,
            'righe': _righe_rack(rack),
            'allegati_pdf': allegati_pdf,
            'allegati_non_pdf': allegati_non_pdf,
        }, request))
        for allegato in allegati_pdf:
            with allegato.file.open('rb') as f:
                blocchi.append(f.read())

    pdf_bytes = _unisci_pdf(blocchi)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f'report-rack-{slugify(progetto.nome)}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
