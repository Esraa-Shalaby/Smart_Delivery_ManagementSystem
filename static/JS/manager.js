/* ============================================================
   manager.js
   Manager-only behaviour: <dialog> modals (warehouses).
   ============================================================ */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {

        // ---------- Open dialog (create / edit) ----------
        document.querySelectorAll('[data-modal-open]').forEach(function (trigger) {
            trigger.addEventListener('click', function () {
                var dialog = document.getElementById(trigger.dataset.modalOpen);
                if (!dialog || typeof dialog.showModal !== 'function') return;

                var form = dialog.querySelector('form');
                var title = dialog.querySelector('[data-modal-title]');
                var isEdit = trigger.dataset.mode === 'edit';

                if (form) {
                    form.reset();
                    if (isEdit) {
                        form.action = trigger.dataset.action || form.action;
                        ['name', 'code', 'address', 'city', 'phone', 'latitude', 'longitude']
                            .forEach(function (key) {
                                var field = form.elements[key];
                                if (field) field.value = trigger.dataset[key] || '';
                            });
                        var active = form.elements['is_active'];
                        if (active) active.checked = trigger.dataset.active === '1';
                    } else if (form.dataset.createAction) {
                        form.action = form.dataset.createAction;
                    }
                }

                if (title) {
                    title.textContent = isEdit
                        ? (title.dataset.titleEdit || title.textContent)
                        : (title.dataset.titleCreate || title.textContent);
                }

                dialog.showModal();
            });
        });

        // ---------- Close dialog ----------
        document.querySelectorAll('[data-modal-close]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var dialog = btn.closest('dialog');
                if (dialog) dialog.close();
            });
        });

        // Click on the backdrop closes the dialog
        document.querySelectorAll('dialog.modal').forEach(function (dialog) {
            dialog.addEventListener('click', function (e) {
                if (e.target === dialog) dialog.close();
            });
        });
    });
})();
