<?php
/**
 * Run this inside the container to install CRigaPreventivo hooks:
 * docker exec espocrm-espocrm-1 php /tmp/install_hooks.php
 */

$dir = '/var/www/html/custom/Espo/Custom/Hooks/CRigaPreventivo';
if (!is_dir($dir)) {
    mkdir($dir, 0755, true);
}

$afterSave = <<<'PHP'
<?php
namespace Espo\Custom\Hooks\CRigaPreventivo;
use Espo\ORM\Entity;

class AfterSave
{
    public static $order = 9;

    public function __construct(
        private \Espo\Core\ORM\EntityManager $entityManager
    ) {}

    public function run(Entity $entity, array $options = []): void
    {
        $this->ricalcolaTotali($entity->get('preventivoId'));
    }

    private function ricalcolaTotali(?string $preventivoId): void
    {
        if (!$preventivoId) return;

        $preventivo = $this->entityManager->getEntity('CPreventivo', $preventivoId);
        if (!$preventivo) return;

        $righe = $this->entityManager->getRepository('CRigaPreventivo')
            ->where(['preventivoId' => $preventivoId])
            ->find();

        $totaleNetto = 0.0;
        foreach ($righe as $riga) {
            $totaleNetto += floatval($riga->get('totaleRiga') ?? 0);
        }

        $sconto = floatval($preventivo->get('scontoGlobale') ?? 0);
        $totaleFinale = $totaleNetto * (1 - $sconto / 100);

        $preventivo->set('totaleNetto', round($totaleNetto, 2));
        $preventivo->set('totaleFinale', round($totaleFinale, 2));
        $this->entityManager->saveEntity($preventivo, ['skipHooks' => true, 'silent' => true]);
    }
}
PHP;

$afterRemove = <<<'PHP'
<?php
namespace Espo\Custom\Hooks\CRigaPreventivo;
use Espo\ORM\Entity;

class AfterRemove
{
    public static $order = 9;

    public function __construct(
        private \Espo\Core\ORM\EntityManager $entityManager
    ) {}

    public function run(Entity $entity, array $options = []): void
    {
        $preventivoId = $entity->get('preventivoId');
        if (!$preventivoId) return;

        $preventivo = $this->entityManager->getEntity('CPreventivo', $preventivoId);
        if (!$preventivo) return;

        $righe = $this->entityManager->getRepository('CRigaPreventivo')
            ->where(['preventivoId' => $preventivoId])
            ->find();

        $totaleNetto = 0.0;
        foreach ($righe as $riga) {
            $totaleNetto += floatval($riga->get('totaleRiga') ?? 0);
        }

        $sconto = floatval($preventivo->get('scontoGlobale') ?? 0);
        $totaleFinale = $totaleNetto * (1 - $sconto / 100);

        $preventivo->set('totaleNetto', round($totaleNetto, 2));
        $preventivo->set('totaleFinale', round($totaleFinale, 2));
        $this->entityManager->saveEntity($preventivo, ['skipHooks' => true, 'silent' => true]);
    }
}
PHP;

file_put_contents($dir . '/AfterSave.php', $afterSave);
file_put_contents($dir . '/AfterRemove.php', $afterRemove);

// Verify syntax
$outSave   = shell_exec('php -l ' . $dir . '/AfterSave.php');
$outRemove = shell_exec('php -l ' . $dir . '/AfterRemove.php');

echo "AfterSave:   $outSave";
echo "AfterRemove: $outRemove";

// Clear EspoCRM cache
$cacheDir = '/var/www/html/data/cache';
if (is_dir($cacheDir)) {
    shell_exec('rm -rf ' . $cacheDir . '/*');
    echo "Cache cleared.\n";
}

echo "Done.\n";
