define(['views/edit'], function(EditView) {
    console.log('[CRigaPreventivo edit.js] FILE CARICATO');
    return EditView.extend({
        exit: function(after) {
            var prevId = this.model.get('preventivoId');
            console.log('[exit] after=' + after + ' preventivoId=' + prevId);
            console.log('[exit] model keys:', Object.keys(this.model.attributes).join(', '));
            if (after === 'save' || after === 'notModified') {
                if (prevId) {
                    this.getRouter().navigate('#CPreventivo/view/' + prevId, {trigger: true});
                    return;
                }
            }
            EditView.prototype.exit.call(this, after);
        }
    });
});
