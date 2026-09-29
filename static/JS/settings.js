document.addEventListener('DOMContentLoaded', () => {
    const root = document.querySelector('[data-settings]');
    if (!root) return;

    const tabs = [...root.querySelectorAll('[data-settings-tab]')];
    const panels = [...root.querySelectorAll('[data-settings-panel]')];
    if (!tabs.length || !panels.length) return;

    const activate = (id, updateHash = true) => {
        const target = panels.find((p) => p.id === id) || panels[0];

        panels.forEach((p) => { p.hidden = p !== target; });
        tabs.forEach((t) => {
            const on = t.getAttribute('href') === '#' + target.id;
            t.classList.toggle('is-active', on);
            if (on) t.setAttribute('aria-current', 'page');
            else t.removeAttribute('aria-current');
        });

        if (updateHash) history.replaceState(null, '', '#' + target.id);
    };

    tabs.forEach((t) => {
        t.addEventListener('click', (e) => {
            e.preventDefault();
            activate(t.getAttribute('href').slice(1));
        });
    });

    // Priority: section with errors > URL hash > server-provided section > first
    const withError = panels.find((p) => p.querySelector('.field--error, .form-alert--error'));
    const fromHash = location.hash ? location.hash.slice(1) : '';
    const fromServer = 'tab-' + (root.dataset.activeSection || 'general');

    activate(withError ? withError.id : (fromHash || fromServer), false);
});