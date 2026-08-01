"""Stringhe statiche del report PDF, tradotte nelle lingue supportate.

I dati compilati dall'utente (nomi pannelli, descrizioni, ecc.) restano
quelli inseriti e non vengono tradotti: solo le etichette fisse dei
template lo sono."""

TESTI = {
    'it': {
        'report_generato_il': 'Report generato il',
        'alle': 'alle',
        'data_intervento': 'Data intervento',
        'titolo_schema': 'Schema rack',
        'nessun_pannello': 'Nessun pannello.',
        'porte': 'porte',
        'tipo_patch_panel': 'Patch panel',
        'tipo_cassetto_fibra': 'Cassetto fibra',
        'data_ports': 'Data Ports',
        'cable_n': 'CABLE N°',
        'tipo_cavo': 'Tipo cavo',
        'descrizione': 'Descrizione',
        'pos_campo': 'Pos. in campo',
        'fluke_check': 'FLUKE Check',
        'allegati': 'Allegati',
    },
    'en': {
        'report_generato_il': 'Report generated on',
        'alle': 'at',
        'data_intervento': 'Intervention date',
        'titolo_schema': 'Rack layout',
        'nessun_pannello': 'No panels.',
        'porte': 'ports',
        'tipo_patch_panel': 'Patch panel',
        'tipo_cassetto_fibra': 'Fiber cassette',
        'data_ports': 'Data Ports',
        'cable_n': 'CABLE N°',
        'tipo_cavo': 'Cable type',
        'descrizione': 'Description',
        'pos_campo': 'Field position',
        'fluke_check': 'FLUKE Check',
        'allegati': 'Attachments',
    },
    'de': {
        'report_generato_il': 'Bericht erstellt am',
        'alle': 'um',
        'data_intervento': 'Interventionsdatum',
        'titolo_schema': 'Rack-Schema',
        'nessun_pannello': 'Keine Paneele.',
        'porte': 'Ports',
        'tipo_patch_panel': 'Patch-Panel',
        'tipo_cassetto_fibra': 'Glasfaser-Kassette',
        'data_ports': 'Data Ports',
        'cable_n': 'KABEL-NR.',
        'tipo_cavo': 'Kabeltyp',
        'descrizione': 'Beschreibung',
        'pos_campo': 'Position vor Ort',
        'fluke_check': 'FLUKE-Check',
        'allegati': 'Anhänge',
    },
}


def testi(lingua):
    return TESTI.get(lingua, TESTI['it'])
