<?php
require_once '/var/www/html/bootstrap.php';
$app = new \Espo\Core\Application();
$app->setupSystemUser();
$em = $app->getContainer()->get('entityManager');

$preventivoId = '69fe4c364d68787f1';

$preventivo = $em->getEntity('CPreventivo', $preventivoId);
if (!$preventivo) {
    echo "PREVENTIVO NON TROVATO\n";
    exit(1);
}

echo "Preventivo trovato: " . $preventivo->get('id') . "\n";
echo "totaleNetto attuale: " . $preventivo->get('totaleNetto') . "\n";
echo "scontoGlobale: " . $preventivo->get('scontoGlobale') . "\n\n";

$righe = $em->getRepository('CRigaPreventivo')
    ->where(['preventivoId' => $preventivoId])
    ->find();

$totaleNetto = 0.0;
foreach ($righe as $r) {
    echo "  riga " . $r->get('id') . " totaleRiga: " . $r->get('totaleRiga') . "\n";
    $totaleNetto += floatval($r->get('totaleRiga') ?? 0);
}

$sconto = floatval($preventivo->get('scontoGlobale') ?? 0);
$totaleFinale = $totaleNetto * (1 - $sconto / 100);

echo "\nCalcolato totaleNetto: " . round($totaleNetto, 2) . "\n";
echo "Calcolato totaleFinale: " . round($totaleFinale, 2) . "\n";

$preventivo->set('totaleNetto', round($totaleNetto, 2));
$preventivo->set('totaleFinale', round($totaleFinale, 2));
$em->saveEntity($preventivo, ['skipHooks' => true, 'silent' => true]);
echo "\nSalvato! Rileggo dal DB...\n";

$preventivo2 = $em->getEntity('CPreventivo', $preventivoId);
echo "totaleNetto nel DB ora: " . $preventivo2->get('totaleNetto') . "\n";
echo "totaleFinale nel DB ora: " . $preventivo2->get('totaleFinale') . "\n";
