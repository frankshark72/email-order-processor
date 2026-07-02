<?php
/**
 * Aggiunge campi trasporto a CPreventivo e auto-copia da CCondizioniCommerciali
 * docker exec espocrm-espocrm-1 php /tmp/add_trasporto_preventivo.php
 */

// 1. Aggiungi campi trasporto a CPreventivo
$path = '/var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs/CPreventivo.json';
$data = json_decode(file_get_contents($path), true);

$data['fields']['tipoCalcoloTrasporto'] = [
    'type' => 'enum',
    'options' => [
        'Sempre gratis',
        'Porto franco sopra soglia',
        'Percentuale sul totale',
        'Percentuale con porto franco',
        'Percentuale con limiti',
        'A quotare',
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

file_put_contents($path, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
echo "Campi trasporto aggiunti a CPreventivo.\n";

// 2. Aggiungi label italiane
$langPath = '/var/www/html/custom/Espo/Custom/Resources/i18n/it_IT/CPreventivo.json';
$lang = file_exists($langPath) ? json_decode(file_get_contents($langPath), true) : [];

$lang['fields'] = $lang['fields'] ?? [];
$lang['fields']['tipoCalcoloTrasporto'] = 'Tipo Calcolo Trasporto';
$lang['fields']['portoFranco'] = 'Porto Franco';
$lang['fields']['sogliaPortoFranco'] = 'Soglia Porto Franco';
$lang['fields']['descrizioneTrasporto'] = 'Descrizione Trasporto';
$lang['fields']['noteTrasporto'] = 'Note Trasporto';

$lang['options'] = $lang['options'] ?? [];
$lang['options']['tipoCalcoloTrasporto'] = [
    'Sempre gratis' => 'Sempre gratis',
    'Porto franco sopra soglia' => 'Porto franco sopra soglia',
    'Percentuale sul totale' => 'Percentuale sul totale',
    'Percentuale con porto franco' => 'Percentuale con porto franco',
    'Percentuale con limiti' => 'Percentuale con limiti',
    'A quotare' => 'A quotare',
    'Personalizzato' => 'Personalizzato',
];

// Assicuriamoci che la directory esista
$langDir = dirname($langPath);
if (!is_dir($langDir)) {
    mkdir($langDir, 0755, true);
}

file_put_contents($langPath, json_encode($lang, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
echo "Label italiane aggiunte.\n";

// 3. Pulisci cache e rebuild
shell_exec('rm -rf /var/www/html/data/cache/*');
echo "Cache pulita.\n";
echo "Done. Ora esegui: php /var/www/html/command.php rebuild\n";
