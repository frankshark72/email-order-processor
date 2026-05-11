define(['views/edit'], function(EditView) {
    return EditView.extend({
        exit: function(after) {
            console.log('[CRigaPreventivo edit.js] exit called, after=' + after);
            console.log('[CRigaPreventivo edit.js] model fields:', JSON.stringify(this.model.attributes));
            if (after === 'save') {
                var prevId = this.model.get('preventivoId');
                console.log('[CRigaPreventivo edit.js] preventivoId=' + prevId);
                if (prevId) {
                    this.getRouter().navigate('#CPreventivo/view/' + prevId, {trigger: true});
                    return;
                }
            }
            EditView.prototype.exit.call(this, after);
        }
    });
});
