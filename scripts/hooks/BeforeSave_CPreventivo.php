<?php
namespace Espo\Custom\Hooks\CPreventivo;
use Espo\ORM\Entity;

class BeforeSave
{
    public static $order = 9;

    public function __construct(
        private \Espo\Core\ORM\EntityManager $entityManager
    ) {}

    public function beforeSave(Entity $entity, array $options = []): void
    {
        $clienteId = $entity->get('clienteId');
        if (!$clienteId) return;
        if (!$entity->isNew() && !$entity->isAttributeChanged('clienteId')) return;

        $condizioni = $this->entityManager->getRepository('CCondizioniCommerciali')
            ->where(['condizioniCommercialiClienteId' => $clienteId, 'attivo' => true])
            ->findOne();

        if (!$condizioni) return;

        $entity->set('tipoCalcoloTrasporto', $condizioni->get('tipoCalcoloTrasporto'));
        $entity->set('portoFranco', $condizioni->get('portoFranco'));
        $entity->set('sogliaPortoFranco', $condizioni->get('sogliaPortoFranco'));
        $entity->set('sogliaPortoFrancoCurrency', $condizioni->get('sogliaPortoFrancoCurrency'));
        $entity->set('descrizioneTrasporto', $condizioni->get('descrizioneTrasporto'));
        $entity->set('noteTrasporto', $condizioni->get('noteTrasporto'));
    }
}
