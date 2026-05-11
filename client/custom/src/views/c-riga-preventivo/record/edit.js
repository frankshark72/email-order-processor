define(['views/record/edit'], function(EditView) {
    return EditView.extend({
        setup: function() {
            EditView.prototype.setup.call(this);
            this.listenTo(this.model, 'change:prodottoId', this.onProdottoChange.bind(this));
            this.listenTo(this.model, 'change:quantita change:prezzoUnitario change:sconto', this.calcolaTotale.bind(this));
        },

        afterSave: function() {
            console.log('[record/edit afterSave] preventivoId=' + this.model.get('preventivoId'));
            var prevId = this.model.get('preventivoId');
            if (prevId) {
                this.getRouter().navigate('#CPreventivo/view/' + prevId, {trigger: true});
                return;
            }
            EditView.prototype.afterSave.call(this);
        },

        onProdottoChange: function() {
            var prodottoId = this.model.get('prodottoId');
            if (!prodottoId) return;
            var self = this;
            this.getModelFactory().create('CProdotto', function(prodotto) {
                prodotto.id = prodottoId;
                prodotto.fetch({
                    success: function() {
                        self.model.set('codiceProdotto', prodotto.get('codice') || '');
                        self.model.set('descrizione', prodotto.get('name') || '');
                        self.model.set('prezzoUnitario', prodotto.get('prezzoListino') || 0);
                        self.calcolaTotale();
                    }
                });
            });
        },

        calcolaTotale: function() {
            var q = parseFloat(this.model.get('quantita') || 0);
            var p = parseFloat(this.model.get('prezzoUnitario') || 0);
            var s = parseFloat(this.model.get('sconto') || 0);
            var totale = q * p * (1 - s / 100);
            this.model.set('totaleRiga', Math.round(totale * 100) / 100);
        }
    });
});
