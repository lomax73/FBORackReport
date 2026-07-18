from django import forms
from django.forms import inlineformset_factory

from . import portal_client
from .models import ElementoRack, Posizione, Progetto, Rack


class ProgettoForm(forms.ModelForm):
    cliente = forms.ChoiceField(label='Cliente')

    class Meta:
        model = Progetto
        fields = ['nome', 'sito', 'data_intervento', 'note']
        widgets = {
            'data_intervento': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [('', '— seleziona —')]
        try:
            clienti = portal_client.list_clienti()
        except portal_client.PortalUnavailableError as exc:
            self.fields['cliente'].help_text = (
                f"Impossibile contattare l'anagrafica clienti nel Portale: {exc}"
            )
        else:
            choices += [(c['id'], c['ragione_sociale']) for c in clienti]
        self.fields['cliente'].choices = choices
        if self.instance and self.instance.pk and self.instance.cliente_id:
            self.fields['cliente'].initial = str(self.instance.cliente_id)

    def clean_cliente(self):
        valore = self.cleaned_data['cliente']
        if not valore:
            raise forms.ValidationError('Seleziona un cliente.')
        return valore

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.cliente_id = self.cleaned_data['cliente']
        if commit:
            instance.save()
        return instance


class RackForm(forms.ModelForm):
    class Meta:
        model = Rack
        fields = ['nome', 'note', 'ordine']


class ElementoRackForm(forms.ModelForm):
    class Meta:
        model = ElementoRack
        fields = ['tipo', 'etichetta', 'n_posizioni', 'ordine']


PosizioneFormSet = inlineformset_factory(
    ElementoRack,
    Posizione,
    fields=['cavo_n', 'tipo_cavo', 'descrizione', 'posizione_in_campo', 'esito_test'],
    extra=0,
    can_delete=False,
)
