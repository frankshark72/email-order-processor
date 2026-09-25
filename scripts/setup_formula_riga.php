<?php
/**
 * Aggiunge formula beforeSave a CRigaPreventivo:
 * - Auto-fill codice, descrizione, prezzo da CProdotto selezionato
 * - Calcolo automatico totaleRiga = quantita * prezzoUnitario * (1 - sconto%)
 */

$path = '/var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs/CRigaPreventivo.json';
$data = json_decode(file_get_contents($path), true);

$data['formula'] = [
    'beforeSave' => implode("\n", [
        "ifThen(prodottoId, codiceProdotto = record\\attribute('CProdotto', prodottoId, 'codice'));",
        "ifThen(prodottoId, descrizione = record\\attribute('CProdotto', prodottoId, 'name'));",
        "ifThen(prodottoId, prezzoUnitario = record\\attribute('CProdotto', prodottoId, 'prezzoListino'));",
        "\$sc = ifThen(sconto, sconto, 0);",
        "totaleRiga = numeric\\multiply(quantita, numeric\\multiply(prezzoUnitario, numeric\\subtract(1, numeric\\divide(\$sc, 100))));",
    ]),
];

file_put_contents($path, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
echo "OK: formula aggiunta a CRigaPreventivo\n";
