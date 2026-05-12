define(['views/edit'], function(EditView) {
    return EditView.extend({
        setup: function() {
            EditView.prototype.setup.call(this);
            document.addEventListener('click', function(e) {
                var el = e.target;
                for (var i = 0; i < 5; i++) {
                    if (!el) break;
                    if (el.dataset && el.dataset.action) {
                        console.log('[CLICK] data-action=' + el.dataset.action);
                        break;
                    }
                    el = el.parentElement;
                }
            }, true);
        },
        afterSave: function() {
            var prevId = this.model.get('preventivoId');
            if (prevId) {
                this.getRouter().navigate('#CPreventivo/view/' + prevId, {trigger: true});
                return;
            }
            EditView.prototype.afterSave.call(this);
        },
        actionCancel: function() {
            var prevId = this.model.get('preventivoId');
            if (prevId) {
                this.getRouter().navigate('#CPreventivo/view/' + prevId, {trigger: true});
                return;
            }
            EditView.prototype.actionCancel.call(this);
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
