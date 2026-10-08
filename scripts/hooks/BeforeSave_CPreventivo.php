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
        $brand = $entity->get('brand');

        if (!$clienteId || !$brand) return;

        $clienteChanged = $entity->isNew() || $entity->isAttributeChanged('clienteId');
        $brandChanged = $entity->isNew() || $entity->isAttributeChanged('brand');

        if (!$clienteChanged && !$brandChanged) return;

        if ($brand === 'Misto') {
            $entity->set('tipoCalcoloTrasporto', 'Da calcolare');
            $entity->set('portoFranco', false);
            $entity->set('sogliaPortoFranco', null);
            $entity->set('descrizioneTrasporto', 'Preventivo misto - spese da calcolare');
            $entity->set('noteTrasporto', '');
            $entity->set('modalitaPagamento', null);
            $entity->set('giorniPagamento', '');
            $entity->set('descrizionePagamento', '');
            return;
        }

        $condizioni = $this->entityManager->getRepository('CCondizioniCommerciali')
            ->where([
                'condizioniCommercialiClienteId' => $clienteId,
                'brand' => $brand,
                'attivo' => true,
            ])
            ->findOne();

        if (!$condizioni) return;

        $entity->set('tipoCalcoloTrasporto', $condizioni->get('tipoCalcoloTrasporto'));
        $entity->set('portoFranco', $condizioni->get('portoFranco'));
        $entity->set('sogliaPortoFranco', $condizioni->get('sogliaPortoFranco'));
        $entity->set('sogliaPortoFrancoCurrency', $condizioni->get('sogliaPortoFrancoCurrency'));
        $entity->set('descrizioneTrasporto', $condizioni->get('descrizioneTrasporto'));
        $entity->set('noteTrasporto', $condizioni->get('noteTrasporto'));
        $entity->set('modalitaPagamento', $condizioni->get('modalitaPagamento'));
        $entity->set('giorniPagamento', $condizioni->get('giorniPagamento'));
        $entity->set('descrizionePagamento', $condizioni->get('descrizionePagamento'));
    }
}
