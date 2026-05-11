define(['views/edit'], function(EditView) {
    console.log('[CRigaPreventivo edit.js] FILE CARICATO');
    return EditView.extend({
        afterSave: function() {
            console.log('[afterSave] called, preventivoId=' + this.model.get('preventivoId'));
            var prevId = this.model.get('preventivoId');
            if (prevId) {
                this.getRouter().navigate('#CPreventivo/view/' + prevId, {trigger: true});
                return;
            }
            EditView.prototype.afterSave.call(this);
        },
        exit: function(after) {
            console.log('[exit] after=' + after + ' preventivoId=' + this.model.get('preventivoId'));
            if (after === 'notModified') {
                var prevId = this.model.get('preventivoId');
                if (prevId) {
                    this.getRouter().navigate('#CPreventivo/view/' + prevId, {trigger: true});
                    return;
                }
            }
            EditView.prototype.exit.call(this, after);
        }
    });
});
