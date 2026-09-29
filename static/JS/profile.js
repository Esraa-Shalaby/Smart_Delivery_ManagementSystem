document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('[data-edit-form]');
    if (!form) return;

    const fields = form.querySelector('[data-edit-fields]');
    const actions = form.querySelector('[data-edit-actions]');
    const startBtn = document.querySelector('[data-edit-start]');
    const cancelBtn = form.querySelector('[data-edit-cancel]');
    const hasErrors = form.hasAttribute('data-has-errors');

    const setEditing = (editing) => {
        fields.disabled = !editing;
        actions.hidden = !editing;
        if (startBtn) startBtn.hidden = editing;
        form.classList.toggle('is-editing', editing);
    };

    // Locked by default; stay editable if the server returned validation errors
    setEditing(hasErrors);

    if (startBtn) {
        startBtn.addEventListener('click', () => {
            setEditing(true);
            const first = fields.querySelector('input');
            if (first) first.focus();
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            form.reset();
            setEditing(false);
        });
    }
});