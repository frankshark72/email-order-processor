define(['views/edit'], function(EditView) {
    return EditView.extend({
        setup: function() {
            EditView.prototype.setup.call(this);
        },
        afterSave: function() {
            var prevId = this.model.get('preventivoId');
            if (prevId) {
                this.getRouter().navigate('#CPreventivo/view/' + prevId, {trigger: true});
                return;
            }
            EditView.prototype.afterSave.call(this);
        },
        exit: function(after) {
            if (after === 'notModified' || after === 'cancel') {
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
