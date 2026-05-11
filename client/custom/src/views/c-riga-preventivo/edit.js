define(['views/edit'], function(EditView) {
    console.log('[CRigaPreventivo edit.js] FILE CARICATO');
    return EditView.extend({
        setup: function() {
            console.log('[SETUP] page edit view, preventivoId=' + this.model.get('preventivoId'));
            EditView.prototype.setup.call(this);
        },
        afterSave: function() {
            console.log('[afterSave] page edit view');
            var prevId = this.model.get('preventivoId');
            if (prevId) {
                this.getRouter().navigate('#CPreventivo/view/' + prevId, {trigger: true});
                return;
            }
            EditView.prototype.afterSave.call(this);
        },
        exit: function(after) {
            console.log('[exit] page edit view, after=' + after);
            if (after === 'save' || after === 'notModified') {
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
