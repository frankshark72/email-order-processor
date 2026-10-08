<?php
/**
 * Crea entità CPrezziNettiCustom in EspoCRM.
 * Esecuzione: docker exec espocrm-espocrm-1 php /tmp/setup_prezzi_netti_custom.php
 */

define('CUSTOM', '/var/www/html/custom/Espo/Custom/Resources');

function mk(string $path, array $data): void {
    $dir = dirname($path);
    if (!is_dir($dir)) mkdir($dir, 0755, true);
    file_put_contents($path, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    echo "  ✓ $path\n";
}

echo "\n=== 1. Scopes ===\n";
mk(CUSTOM . '/metadata/scopes/CPrezziNettiCustom.json', [
    "entity"        => true,
    "object"        => true,
    "tab"           => true,
    "type"          => "BasePlus",
    "module"        => "Custom",
    "stream"        => false,
    "disabled"      => false,
    "importable"    => true,
    "customizable"  => true,
    "isCustom"      => true,
    "color"         => "#4a90e2",
    "iconClass"     => "fas fa-tag",
]);

echo "\n=== 2. EntityDefs ===\n";
mk(CUSTOM . '/metadata/entityDefs/CPrezziNettiCustom.json', [
    "fields" => [
        "name"               => ["type" => "varchar", "maxLength" => 255],
        "attivo"             => ["type" => "bool", "default" => true, "audited" => true],
        "codiceProdotto"     => ["type" => "varchar", "maxLength" => 100, "required" => true, "audited" => true],
        "descrizioneProdotto"=> ["type" => "varchar", "maxLength" => 200],
        "prezzoNetto"        => ["type" => "currency", "required" => true, "audited" => true],
        "note"               => ["type" => "text"],
        "dataInizio"         => ["type" => "date", "audited" => true],
        "dataFine"           => ["type" => "date", "audited" => true],
        "cliente"            => ["type" => "link"],
        "clienteId"          => ["type" => "foreignId", "index" => true],
        "clienteName"        => ["type" => "foreign", "link" => "cliente", "field" => "name"],
        "fornitore"          => ["type" => "link"],
        "fornitoreId"        => ["type" => "foreignId", "index" => true],
        "fornitoreName"      => ["type" => "foreign", "link" => "fornitore", "field" => "name"],
    ],
    "links" => [
        "cliente" => [
            "type"        => "belongsTo",
            "entity"      => "Account",
            "foreign"     => "prezziNettiCustomCliente",
            "foreignName" => "name",
        ],
        "fornitore" => [
            "type"        => "belongsTo",
            "entity"      => "Account",
            "foreign"     => "prezziNettiCustomFornitore",
            "foreignName" => "name",
        ],
    ],
    "textFilterFields" => ["name", "codiceProdotto", "descrizioneProdotto"],
    "orderBy"          => "createdAt",
    "orderDirection"   => "desc",
]);

echo "\n=== 3. Account — relazioni inverse ===\n";
$accPath = CUSTOM . '/metadata/entityDefs/Account.json';
$acc = file_exists($accPath) ? json_decode(file_get_contents($accPath), true) : [];
if (!isset($acc['relationships'])) $acc['relationships'] = [];
$acc['relationships']['prezziNettiCustomCliente'] = [
    "type"   => "hasMany",
    "entity" => "CPrezziNettiCustom",
    "foreign"=> "cliente",
];
$acc['relationships']['prezziNettiCustomFornitore'] = [
    "type"   => "hasMany",
    "entity" => "CPrezziNettiCustom",
    "foreign"=> "fornitore",
];
mk($accPath, $acc);

echo "\n=== 4. Layout Detail ===\n";
mk(CUSTOM . '/layouts/CPrezziNettiCustom/detail.json', [
    [
        "label" => "Identificazione",
        "rows"  => [
            [["name" => "name", "fullWidth" => true]],
            [["name" => "cliente"], ["name" => "fornitore"]],
            [["name" => "attivo"], false],
        ],
    ],
    [
        "label" => "Prodotto e Prezzo",
        "rows"  => [
            [["name" => "codiceProdotto"], ["name" => "prezzoNetto"]],
            [["name" => "descrizioneProdotto", "fullWidth" => true]],
            [["name" => "note", "fullWidth" => true]],
        ],
    ],
    [
        "label" => "Validità",
        "rows"  => [
            [["name" => "dataInizio"], ["name" => "dataFine"]],
        ],
    ],
]);

echo "\n=== 5. Layout List ===\n";
mk(CUSTOM . '/layouts/CPrezziNettiCustom/list.json', [
    ["name" => "cliente",             "link" => true],
    ["name" => "fornitore"],
    ["name" => "codiceProdotto"],
    ["name" => "descrizioneProdotto"],
    ["name" => "prezzoNetto"],
    ["name" => "dataInizio"],
    ["name" => "dataFine"],
    ["name" => "attivo"],
]);

echo "\n=== 6. Labels (it_IT) ===\n";
$i18nDir = CUSTOM . '/i18n/it_IT';
if (!is_dir($i18nDir)) mkdir($i18nDir, 0755, true);
mk($i18nDir . '/CPrezziNettiCustom.json', [
    "fields" => [
        "name"                => "Nome",
        "attivo"              => "Attivo",
        "codiceProdotto"      => "Codice Prodotto",
        "descrizioneProdotto" => "Descrizione Prodotto",
        "prezzoNetto"         => "Prezzo Netto",
        "note"                => "Note",
        "dataInizio"          => "Data Inizio",
        "dataFine"            => "Data Fine",
        "cliente"             => "Cliente",
        "clienteName"         => "Cliente",
        "fornitore"           => "Fornitore",
        "fornitoreName"       => "Fornitore",
    ],
    "links" => [
        "cliente"   => "Cliente",
        "fornitore" => "Fornitore",
        "prezziNettiCustomCliente"   => "Prezzi Netti Custom (come Cliente)",
        "prezziNettiCustomFornitore" => "Prezzi Netti Custom (come Fornitore)",
    ],
]);

// Labels globali per il nome entità
$globalI18n = $i18nDir . '/Global.json';
$global = file_exists($globalI18n) ? json_decode(file_get_contents($globalI18n), true) : [];
if (!isset($global['scopeNames'])) $global['scopeNames'] = [];
if (!isset($global['scopeNamesPlural'])) $global['scopeNamesPlural'] = [];
$global['scopeNames']['CPrezziNettiCustom'] = 'Prezzo Netto Custom';
$global['scopeNamesPlural']['CPrezziNettiCustom'] = 'Prezzi Netti Custom';
mk($globalI18n, $global);

echo "\n=== COMPLETATO ===\n";
echo "Ora esegui: docker exec espocrm-espocrm-1 php command.php rebuild\n\n";
