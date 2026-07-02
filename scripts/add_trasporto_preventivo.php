<?php
/**
 * Aggiunge campo brand e campi trasporto a CPreventivo
 * docker exec espocrm-espocrm-1 php /tmp/add_trasporto_preventivo.php
 */

$path = '/var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs/CPreventivo.json';
$data = json_decode(file_get_contents($path), true);

// Campo brand con opzione Misto
$data['fields']['brand'] = [
    'type' => 'enum',
    'required' => true,
    'options' => [
        'EL.MO.',
        'RIB',
        '4POWER',
        'Prospecta',
        'ERMES',
        'Misto',
    ],
    'style' => [
        'EL.MO.' => null,
        'RIB' => null,
        '4POWER' => null,
        'Prospecta' => null,
        'ERMES' => null,
        'Misto' => null,
    ],
    'default' => 'EL.MO.',
    'maxLength' => 100,
    'isCustom' => true,
];

// Campi trasporto
$data['fields']['tipoCalcoloTrasporto'] = [
    'type' => 'enum',
    'options' => [
        'Sempre gratis',
        'Porto franco sopra soglia',
        'Percentuale sul totale',
        'Percentuale con porto franco',
        'Percentuale con limiti',
        'A quotare',
        'Da calcolare',
        'Personalizzato',
    ],
    'default' => 'Sempre gratis',
    'maxLength' => 100,
    'isCustom' => true,
];

$data['fields']['portoFranco'] = [
    'type' => 'bool',
    'notNull' => true,
    'default' => false,
    'isCustom' => true,
];

$data['fields']['sogliaPortoFranco'] = [
    'type' => 'currency',
    'isCustom' => true,
];

$data['fields']['descrizioneTrasporto'] = [
    'type' => 'varchar',
    'maxLength' => 200,
    'isCustom' => true,
];

$data['fields']['noteTrasporto'] = [
    'type' => 'text',
    'rowsMin' => 2,
    'cutHeight' => 200,
    'isCustom' => true,
];

// Campi pagamento (copiati da condizioni commerciali)
$data['fields']['modalitaPagamento'] = [
    'type' => 'enum',
    'options' => [
        'Bonifico',
        'Ricevuta Bancaria',
        'Contanti',
        'Anticipato',
        'Rimessa Diretta',
        'Altro',
    ],
    'default' => 'Bonifico',
    'maxLength' => 100,
    'isCustom' => true,
];

$data['fields']['giorniPagamento'] = [
    'type' => 'varchar',
    'maxLength' => 50,
    'isCustom' => true,
];

$data['fields']['descrizionePagamento'] = [
    'type' => 'varchar',
    'maxLength' => 100,
    'isCustom' => true,
];

file_put_contents($path, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
echo "Campi brand, trasporto e pagamento aggiunti a CPreventivo.\n";

// Label italiane
$langDir = '/var/www/html/custom/Espo/Custom/Resources/i18n/it_IT';
if (!is_dir($langDir)) {
    mkdir($langDir, 0755, true);
}
$langPath = $langDir . '/CPreventivo.json';
$lang = file_exists($langPath) ? json_decode(file_get_contents($langPath), true) : [];

$lang['fields'] = $lang['fields'] ?? [];
$lang['fields']['brand'] = 'Brand / Mandante';
$lang['fields']['tipoCalcoloTrasporto'] = 'Tipo Calcolo Trasporto';
$lang['fields']['portoFranco'] = 'Porto Franco';
$lang['fields']['sogliaPortoFranco'] = 'Soglia Porto Franco';
$lang['fields']['descrizioneTrasporto'] = 'Descrizione Trasporto';
$lang['fields']['noteTrasporto'] = 'Note Trasporto';
$lang['fields']['modalitaPagamento'] = 'Modalità Pagamento';
$lang['fields']['giorniPagamento'] = 'Giorni Pagamento';
$lang['fields']['descrizionePagamento'] = 'Descrizione Pagamento';

$lang['options'] = $lang['options'] ?? [];
$lang['options']['brand'] = [
    'EL.MO.' => 'EL.MO.',
    'RIB' => 'RIB',
    '4POWER' => '4POWER',
    'Prospecta' => 'Prospecta',
    'ERMES' => 'ERMES',
    'Misto' => 'Misto',
];
$lang['options']['tipoCalcoloTrasporto'] = [
    'Sempre gratis' => 'Sempre gratis',
    'Porto franco sopra soglia' => 'Porto franco sopra soglia',
    'Percentuale sul totale' => 'Percentuale sul totale',
    'Percentuale con porto franco' => 'Percentuale con porto franco',
    'Percentuale con limiti' => 'Percentuale con limiti',
    'A quotare' => 'A quotare',
    'Da calcolare' => 'Da calcolare',
    'Personalizzato' => 'Personalizzato',
];
$lang['options']['modalitaPagamento'] = [
    'Bonifico' => 'Bonifico',
    'Ricevuta Bancaria' => 'Ricevuta Bancaria',
    'Contanti' => 'Contanti',
    'Anticipato' => 'Anticipato',
    'Rimessa Diretta' => 'Rimessa Diretta',
    'Altro' => 'Altro',
];

file_put_contents($langPath, json_encode($lang, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
echo "Label italiane aggiunte.\n";

// Pulisci cache
shell_exec('rm -rf /var/www/html/data/cache/*');
echo "Cache pulita.\n";
echo "Done. Ora esegui: php /var/www/html/command.php rebuild\n";
