<?php
/**
 * Crea entità CPreventivo e CRigaPreventivo in EspoCRM.
 * Esecuzione: docker exec espocrm-espocrm-1 php /tmp/setup_preventivi.php
 */

define('CUSTOM', '/var/www/html/custom/Espo/Custom/Resources');
define('CTRL',   '/var/www/html/custom/Espo/Custom/Controllers');

function mk(string $path, array $data): void {
    $dir = dirname($path);
    if (!is_dir($dir)) mkdir($dir, 0755, true);
    file_put_contents($path, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    echo "  ✓ $path\n";
}

// ─────────────────────────────────────────────
// CPreventivo
// ─────────────────────────────────────────────

echo "\n=== 1. Scopes CPreventivo ===\n";
mk(CUSTOM . '/metadata/scopes/CPreventivo.json', [
    "entity"       => true,
    "object"       => true,
    "layouts"      => true,
    "tab"          => true,
    "acl"          => true,
    "aclPortal"    => true,
    "type"         => "BasePlus",
    "module"       => "Custom",
    "stream"       => true,
    "disabled"     => false,
    "importable"   => true,
    "customizable" => true,
    "isCustom"     => true,
    "notifications"=> true,
    "color"        => "#27ae60",
    "iconClass"    => "fas fa-file-invoice",
]);

echo "\n=== 2. EntityDefs CPreventivo ===\n";
mk(CUSTOM . '/metadata/entityDefs/CPreventivo.json', [
    "fields" => [
        "name"              => ["type" => "varchar", "maxLength" => 100, "required" => true],
        "stato"             => ["type" => "enum",
                                "options" => ["bozza","inviato","accettato","rifiutato","scaduto"],
                                "default" => "bozza", "audited" => true],
        "cliente"           => ["type" => "link"],
        "clienteId"         => ["type" => "foreignId", "index" => true],
        "clienteName"       => ["type" => "foreign", "link" => "cliente", "field" => "name"],
        "emailDestinatario" => ["type" => "varchar", "maxLength" => 200],
        "dataPreventivo"    => ["type" => "date", "required" => true],
        "dataScadenza"      => ["type" => "date"],
        "oggettoEmail"      => ["type" => "varchar", "maxLength" => 300],
        "note"              => ["type" => "text"],
        "totaleNetto"       => ["type" => "currency", "readOnly" => true],
        "scontoGlobale"     => ["type" => "float", "min" => 0, "max" => 100, "default" => 0],
        "totaleFinale"      => ["type" => "currency", "readOnly" => true],
    ],
    "links" => [
        "cliente" => [
            "type"        => "belongsTo",
            "entity"      => "Account",
            "foreign"     => "preventivi",
            "foreignName" => "name",
        ],
        "righe" => [
            "type"    => "hasMany",
            "entity"  => "CRigaPreventivo",
            "foreign" => "preventivo",
        ],
    ],
    "textFilterFields" => ["name","clienteName","oggettoEmail"],
    "orderBy"          => "createdAt",
    "orderDirection"   => "desc",
]);

// ─────────────────────────────────────────────
// CRigaPreventivo
// ─────────────────────────────────────────────

echo "\n=== 3. Scopes CRigaPreventivo ===\n";
mk(CUSTOM . '/metadata/scopes/CRigaPreventivo.json', [
    "entity"       => true,
    "object"       => true,
    "layouts"      => true,
    "tab"          => false,
    "acl"          => true,
    "aclPortal"    => true,
    "type"         => "Base",
    "module"       => "Custom",
    "stream"       => false,
    "disabled"     => false,
    "importable"   => false,
    "customizable" => true,
    "isCustom"     => true,
]);

echo "\n=== 4. EntityDefs CRigaPreventivo ===\n";
mk(CUSTOM . '/metadata/entityDefs/CRigaPreventivo.json', [
    "fields" => [
        "name"           => ["type" => "varchar", "maxLength" => 255],
        "preventivo"     => ["type" => "link"],
        "preventivoId"   => ["type" => "foreignId", "index" => true],
        "preventivoName" => ["type" => "foreign", "link" => "preventivo", "field" => "name"],
        "prodotto"       => ["type" => "link"],
        "prodottoId"     => ["type" => "foreignId", "index" => true],
        "prodottoName"   => ["type" => "foreign", "link" => "prodotto", "field" => "name"],
        "codiceProdotto" => ["type" => "varchar", "maxLength" => 100],
        "descrizione"    => ["type" => "varchar", "maxLength" => 300],
        "quantita"       => ["type" => "float", "required" => true, "min" => 0, "default" => 1],
        "unitaMisura"    => ["type" => "varchar", "maxLength" => 20, "default" => "pz"],
        "prezzoUnitario" => ["type" => "currency", "required" => true],
        "sconto"         => ["type" => "float", "min" => 0, "max" => 100, "default" => 0],
        "totaleRiga"     => ["type" => "currency", "readOnly" => true],
    ],
    "links" => [
        "preventivo" => [
            "type"        => "belongsTo",
            "entity"      => "CPreventivo",
            "foreign"     => "righe",
            "foreignName" => "name",
        ],
        "prodotto" => [
            "type"        => "belongsTo",
            "entity"      => "CProdotto",
            "foreign"     => "righePreventivo",
            "foreignName" => "name",
        ],
    ],
    "orderBy"       => "id",
    "orderDirection"=> "asc",
]);

// ─────────────────────────────────────────────
// Relazioni inverse
// ─────────────────────────────────────────────

echo "\n=== 5. Account — relazione inversa ===\n";
$accPath = CUSTOM . '/metadata/entityDefs/Account.json';
$acc = file_exists($accPath) ? json_decode(file_get_contents($accPath), true) : [];
if (!isset($acc['links'])) $acc['links'] = [];
$acc['links']['preventivi'] = [
    "type"    => "hasMany",
    "entity"  => "CPreventivo",
    "foreign" => "cliente",
];
mk($accPath, $acc);

echo "\n=== 6. CProdotto — relazione inversa ===\n";
$prodPath = CUSTOM . '/metadata/entityDefs/CProdotto.json';
$prod = file_exists($prodPath) ? json_decode(file_get_contents($prodPath), true) : [];
if (!isset($prod['links'])) $prod['links'] = [];
$prod['links']['righePreventivo'] = [
    "type"    => "hasMany",
    "entity"  => "CRigaPreventivo",
    "foreign" => "prodotto",
];
mk($prodPath, $prod);

// ─────────────────────────────────────────────
// Layout CPreventivo
// ─────────────────────────────────────────────

echo "\n=== 7. Layout CPreventivo detail ===\n";
mk(CUSTOM . '/layouts/CPreventivo/detail.json', [
    [
        "label" => "Intestazione",
        "rows"  => [
            [["name" => "name"], ["name" => "stato"]],
            [["name" => "cliente"], ["name" => "emailDestinatario"]],
            [["name" => "dataPreventivo"], ["name" => "dataScadenza"]],
        ],
    ],
    [
        "label" => "Totali",
        "rows"  => [
            [["name" => "totaleNetto"], ["name" => "scontoGlobale"]],
            [["name" => "totaleFinale"], false],
        ],
    ],
    [
        "label" => "Comunicazione",
        "rows"  => [
            [["name" => "oggettoEmail", "fullWidth" => true]],
            [["name" => "note", "fullWidth" => true]],
        ],
    ],
]);

echo "\n=== 8. Layout CPreventivo list ===\n";
mk(CUSTOM . '/layouts/CPreventivo/list.json', [
    ["name" => "name",        "link" => true],
    ["name" => "clienteName"],
    ["name" => "stato"],
    ["name" => "dataPreventivo"],
    ["name" => "dataScadenza"],
    ["name" => "totaleNetto"],
    ["name" => "scontoGlobale"],
    ["name" => "totaleFinale"],
]);

// ─────────────────────────────────────────────
// Layout CRigaPreventivo
// ─────────────────────────────────────────────

echo "\n=== 9. Layout CRigaPreventivo detail ===\n";
mk(CUSTOM . '/layouts/CRigaPreventivo/detail.json', [
    [
        "label" => "",
        "rows"  => [
            [["name" => "preventivo"], ["name" => "prodotto"]],
            [["name" => "codiceProdotto"], ["name" => "descrizione"]],
            [["name" => "quantita"], ["name" => "unitaMisura"]],
            [["name" => "prezzoUnitario"], ["name" => "sconto"]],
            [["name" => "totaleRiga"], false],
        ],
    ],
]);

echo "\n=== 10. Layout CRigaPreventivo list (subpanel) ===\n";
mk(CUSTOM . '/layouts/CRigaPreventivo/listSmall.json', [
    ["name" => "codiceProdotto"],
    ["name" => "descrizione"],
    ["name" => "quantita"],
    ["name" => "unitaMisura"],
    ["name" => "prezzoUnitario"],
    ["name" => "sconto"],
    ["name" => "totaleRiga"],
]);

// ─────────────────────────────────────────────
// i18n
// ─────────────────────────────────────────────

echo "\n=== 11. Labels it_IT ===\n";
$i18nDir = CUSTOM . '/i18n/it_IT';
if (!is_dir($i18nDir)) mkdir($i18nDir, 0755, true);

mk($i18nDir . '/CPreventivo.json', [
    "fields" => [
        "name"              => "Numero Preventivo",
        "stato"             => "Stato",
        "cliente"           => "Cliente",
        "clienteName"       => "Cliente",
        "emailDestinatario" => "Email Destinatario",
        "dataPreventivo"    => "Data Preventivo",
        "dataScadenza"      => "Valido Fino Al",
        "oggettoEmail"      => "Oggetto Email",
        "note"              => "Note / Condizioni",
        "totaleNetto"       => "Totale Netto",
        "scontoGlobale"     => "Sconto Globale %",
        "totaleFinale"      => "Totale Finale",
        "righe"             => "Righe Preventivo",
    ],
    "options" => [
        "stato" => [
            "bozza"     => "Bozza",
            "inviato"   => "Inviato",
            "accettato" => "Accettato",
            "rifiutato" => "Rifiutato",
            "scaduto"   => "Scaduto",
        ],
    ],
    "links" => [
        "cliente" => "Cliente",
        "righe"   => "Righe Preventivo",
    ],
]);

mk($i18nDir . '/CRigaPreventivo.json', [
    "fields" => [
        "name"           => "Descrizione",
        "preventivo"     => "Preventivo",
        "preventivoName" => "Preventivo",
        "prodotto"       => "Prodotto",
        "prodottoName"   => "Prodotto",
        "codiceProdotto" => "Codice",
        "descrizione"    => "Descrizione",
        "quantita"       => "Qtà",
        "unitaMisura"    => "U.M.",
        "prezzoUnitario" => "Prezzo Unitario",
        "sconto"         => "Sconto %",
        "totaleRiga"     => "Totale Riga",
    ],
    "links" => [
        "preventivo" => "Preventivo",
        "prodotto"   => "Prodotto",
    ],
]);

$globalI18n = $i18nDir . '/Global.json';
$global = file_exists($globalI18n) ? json_decode(file_get_contents($globalI18n), true) : [];
if (!isset($global['scopeNames'])) $global['scopeNames'] = [];
if (!isset($global['scopeNamesPlural'])) $global['scopeNamesPlural'] = [];
$global['scopeNames']['CPreventivo']     = 'Preventivo';
$global['scopeNamesPlural']['CPreventivo'] = 'Preventivi';
$global['scopeNames']['CRigaPreventivo']   = 'Riga Preventivo';
$global['scopeNamesPlural']['CRigaPreventivo'] = 'Righe Preventivo';
mk($globalI18n, $global);

echo "\n=== 13. Controllers ===\n";
foreach (['CPreventivo', 'CRigaPreventivo'] as $entity) {
    $path = CTRL . "/{$entity}.php";
    if (!is_dir(CTRL)) mkdir(CTRL, 0755, true);
    file_put_contents($path, "<?php\nnamespace Espo\\Custom\\Controllers;\nclass {$entity} extends \\Espo\\Core\\Controllers\\Record {}\n");
    echo "  ✓ $path\n";
}

echo "\n=== COMPLETATO ===\n";
echo "Ora esegui: docker exec espocrm-espocrm-1 php command.php rebuild\n\n";
