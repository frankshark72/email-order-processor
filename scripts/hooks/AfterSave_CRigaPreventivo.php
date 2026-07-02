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
