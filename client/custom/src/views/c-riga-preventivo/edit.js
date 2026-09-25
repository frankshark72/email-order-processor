define(['views/edit'], function(EditView) {
    return EditView.extend({
        setup: function() {
            EditView.prototype.setup.call(this);
            var self = this;

            this._cancelHandler = function(e) {
                var el = e.target;
                for (var i = 0; i < 5; i++) {
                    if (!el) break;
                    if (el.dataset && el.dataset.action === 'cancel') {
                        var prevId = self.model.get('preventivoId');
                        if (prevId) {
                            e.stopImmediatePropagation();
                            self.getRouter().navigate('#CPreventivo/view/' + prevId, {trigger: true});
                        }
                        break;
                    }
                    el = el.parentElement;
                }
            };

            document.addEventListener('click', this._cancelHandler, true);
        },

        remove: function() {
            if (this._cancelHandler) {
                document.removeEventListener('click', this._cancelHandler, true);
                this._cancelHandler = null;
            }
            EditView.prototype.remove.call(this);
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
