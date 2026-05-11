define(['views/edit'], function(EditView) {
    console.log('[CRigaPreventivo edit.js] FILE CARICATO');
    return EditView.extend({
        exit: function(after) {
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
