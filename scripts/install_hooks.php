<?php
/**
 * Run this inside the container to install CRigaPreventivo hooks:
 * docker exec espocrm-espocrm-1 php /tmp/install_hooks.php
 */

$dir = '/var/www/html/custom/Espo/Custom/Hooks/CRigaPreventivo';
if (!is_dir($dir)) {
    mkdir($dir, 0755, true);
}

$beforeSave = <<<'PHP'
<?php
namespace Espo\Custom\Hooks\CRigaPreventivo;
use Espo\ORM\Entity;

class BeforeSave
{
    public static $order = 9;

    public function __construct(
        private \Espo\Core\ORM\EntityManager $entityManager
    ) {}

    public function beforeSave(Entity $entity, array $options = []): void
    {
        $prodottoId = $entity->get('prodottoId');
        if ($prodottoId && ($entity->isNew() || $entity->isAttributeChanged('prodottoId'))) {
            $prodotto = $this->entityManager->getEntity('CProdotto', $prodottoId);
            if ($prodotto) {
                $entity->set('codiceProdotto', $prodotto->get('codice'));
                $entity->set('descrizione', $prodotto->get('name'));
                $entity->set('prezzoUnitario', $prodotto->get('prezzoListino'));
            }
        }

        $quantita = floatval($entity->get('quantita') ?? 0);
        $prezzoUnitario = floatval($entity->get('prezzoUnitario') ?? 0);
        $sconto = floatval($entity->get('sconto') ?? 0);
        $totale = $quantita * $prezzoUnitario * (1 - $sconto / 100);
        $entity->set('totaleRiga', round($totale, 4));
    }
}
PHP;

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

    public function afterSave(Entity $entity, array $options = []): void
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

    public function afterRemove(Entity $entity, array $options = []): void
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

file_put_contents($dir . '/BeforeSave.php', $beforeSave);
file_put_contents($dir . '/AfterSave.php', $afterSave);
file_put_contents($dir . '/AfterRemove.php', $afterRemove);

foreach (['BeforeSave', 'AfterSave', 'AfterRemove'] as $name) {
    $out = shell_exec('php -l ' . $dir . '/' . $name . '.php');
    echo "$name: $out";
}

// Clear cache
shell_exec('rm -rf /var/www/html/data/cache/*');
echo "Cache cleared.\n";
echo "Done. Run: php /var/www/html/command.php rebuild\n";
