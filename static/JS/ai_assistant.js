/* ============================================================
   ai_assistant.js
   Full AI Assistant page — chat + action confirmation
   Used by: manager/ai_assistant.html
   ============================================================ */
(function () {
    'use strict';

    const root = document.querySelector('[data-ai-root]');
    if (!root) return;

    /* ============================= ELEMENTS ============================= */
    const conversation = root.querySelector('#ai-conversation');
    const form = root.querySelector('#ai-input-form');
    const input = root.querySelector('#ai-input');
    const sendBtn = root.querySelector('#ai-send-btn');
    const typing = root.querySelector('#ai-typing');
    const suggestions = root.querySelectorAll('[data-prompt]');
    const messageTemplate = root.querySelector('#chat-message-template');

    const clearBtn = root.querySelector('[data-ai-action="clear-conversation"]');
    const newBtn = root.querySelector('[data-ai-action="new-conversation"]');
    const retryBtn = root.querySelector('[data-ai-action="retry"]');

    const confirmModal = root.querySelector('#ai-confirm-modal');
    const confirmText = root.querySelector('#ai-confirm-text');
    const confirmMeta = root.querySelector('#ai-confirm-meta');
    const confirmApprove = root.querySelector('[data-ai-action="approve-confirm"]');
    const confirmCancel = root.querySelectorAll('[data-ai-action="cancel-confirm"]');

    /* ============================= STATE ============================= */
    let conversationHistory = [];      // [{role, content}]
    let lastUserMessage = null;
    let pendingAction = null;          // للـconfirmation

    const ENDPOINT = root.dataset.aiEndpoint || '/manager/ai/chat/';
    const ACTION_ENDPOINT = root.dataset.aiActionEndpoint || '/manager/ai/action/';

    /* ============================= HELPERS ============================= */
    function getCsrfToken() {
        return root.querySelector('[name="csrfmiddlewaretoken"]')?.value
            || document.querySelector('[name="csrfmiddlewaretoken"]')?.value
            || '';
    }

    function getTime() {
        const d = new Date();
        return String(d.getHours()).padStart(2, '0') + ':' +
            String(d.getMinutes()).padStart(2, '0');
    }

    function scrollToBottom() {
        if (conversation) {
            conversation.scrollTop = conversation.scrollHeight;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /* ============================= MESSAGE RENDERING ============================= */
    function renderMessage({ role, content, time, structured }) {
        if (!messageTemplate) return null;

        const node = messageTemplate.content.cloneNode(true);
        const msg = node.querySelector('.chat-message');
        const avatar = node.querySelector('.chat-avatar');
        const author = node.querySelector('.chat-author');
        const timeEl = node.querySelector('.chat-time');
        const contentEl = node.querySelector('.chat-content');

        if (role === 'user') {
            msg.classList.add('chat-message-user');
            avatar.textContent = 'U';
            author.textContent = 'You';
        } else {
            msg.classList.add('chat-message-ai');
            msg.classList.add('chat-message-enter');
            avatar.textContent = '✦';
            author.textContent = 'AI Assistant';
        }

        timeEl.textContent = time || getTime();

        // structured = { type: 'text' | 'list' | 'table' | 'confirmation', ... }
        if (structured) {
            renderStructuredContent(contentEl, structured);
        } else {
            // نص عادي — مع احترام أسطر متعددة
            const paragraphs = String(content || '').split('\n\n');
            paragraphs.forEach((p) => {
                const para = document.createElement('p');
                para.textContent = p;
                contentEl.appendChild(para);
            });
        }

        conversation.appendChild(node);
        scrollToBottom();
        return conversation.lastElementChild;
    }

    function renderStructuredContent(container, structured) {
        // ---------- TEXT ----------
        if (structured.type === 'text') {
            const p = document.createElement('p');
            p.textContent = structured.text || '';
            container.appendChild(p);
            return;
        }

        // ---------- LIST ----------
        if (structured.type === 'list') {
            if (structured.intro) {
                const p = document.createElement('p');
                p.textContent = structured.intro;
                container.appendChild(p);
            }
            const ul = document.createElement('ul');
            (structured.items || []).forEach((item) => {
                const li = document.createElement('li');
                li.textContent = item;
                ul.appendChild(li);
            });
            container.appendChild(ul);
            return;
        }

        // ---------- TABLE ----------
        if (structured.type === 'table') {
            if (structured.intro) {
                const p = document.createElement('p');
                p.textContent = structured.intro;
                container.appendChild(p);
            }
            const wrap = document.createElement('div');
            wrap.className = 'chat-table-wrap';
            const table = document.createElement('table');
            table.className = 'chat-table';

            const thead = document.createElement('thead');
            const headRow = document.createElement('tr');
            (structured.headers || []).forEach((h) => {
                const th = document.createElement('th');
                th.textContent = h;
                headRow.appendChild(th);
            });
            thead.appendChild(headRow);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            (structured.rows || []).forEach((row) => {
                const tr = document.createElement('tr');
                row.forEach((cell) => {
                    const td = document.createElement('td');
                    if (typeof cell === 'object' && cell.badge) {
                        const span = document.createElement('span');
                        span.className = 'status-badge status-' + cell.badge.toLowerCase();
                        span.textContent = cell.text;
                        td.appendChild(span);
                    } else {
                        td.textContent = cell;
                    }
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);

            wrap.appendChild(table);
            container.appendChild(wrap);
            return;
        }

        // ---------- CONFIRMATION ----------
        if (structured.type === 'confirmation') {
            const p = document.createElement('p');
            p.textContent = structured.text || 'Do you want to proceed?';
            container.appendChild(p);

            const card = document.createElement('div');
            card.className = 'ai-confirmation-card';

            const details = document.createElement('div');
            details.className = 'ai-confirmation-details';
            Object.entries(structured.details || {}).forEach(([k, v]) => {
                const row = document.createElement('div');
                row.className = 'ai-confirmation-row';
                const kEl = document.createElement('span');
                kEl.className = 'ai-confirmation-key';
                kEl.textContent = k;
                const vEl = document.createElement('span');
                vEl.className = 'ai-confirmation-value';
                vEl.textContent = v;
                row.appendChild(kEl);
                row.appendChild(vEl);
                details.appendChild(row);
            });
            card.appendChild(details);

            const actions = document.createElement('div');
            actions.className = 'ai-confirmation-actions';

            const confirmBtn = document.createElement('button');
            confirmBtn.type = 'button';
            confirmBtn.className = 'btn btn-primary btn-sm';
            confirmBtn.textContent = 'Confirm Action';
            confirmBtn.addEventListener('click', () => {
                openConfirmModal(structured.action);
            });

            actions.appendChild(confirmBtn);
            card.appendChild(actions);
            container.appendChild(card);
            return;
        }

        // ---------- FALLBACK ----------
        const p = document.createElement('p');
        p.textContent = structured.text || '';
        container.appendChild(p);
    }

    /* ============================= TYPING INDICATOR ============================= */
    function showTyping() {
        if (typing) {
            typing.hidden = false;
            scrollToBottom();
        }
    }

    function hideTyping() {
        if (typing) typing.hidden = true;
    }

    /* ============================= SEND MESSAGE ============================= */
    async function sendMessage(text, options = {}) {
        const trimmed = String(text || '').trim();
        if (!trimmed) return;

        // أضف رسالة المستخدم
        renderMessage({ role: 'user', content: trimmed });
        conversationHistory.push({ role: 'user', content: trimmed });
        lastUserMessage = trimmed;

        // نظّف input
        if (input) {
            input.value = '';
            input.style.height = 'auto';
        }

        // عطّل الإرسال
        setSendingState(true);
        showTyping();

        try {
            const response = await fetch(ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({
                    message: trimmed,
                    history: conversationHistory.slice(-6), // آخر 6 رسائل
                    retry: options.retry === true,
                }),
            });

            hideTyping();
            setSendingState(false);

            if (!response.ok) {
                renderErrorMessage('Sorry, something went wrong. Please try again.');
                return;
            }

            const data = await response.json();

            // تعامل مع أنواع الردود
            if (data.reply) {
                renderMessage({ role: 'ai', content: data.reply });
                conversationHistory.push({ role: 'assistant', content: data.reply });
            } else if (data.structured) {
                renderMessage({ role: 'ai', content: '', structured: data.structured });
                conversationHistory.push({ role: 'assistant', content: data.structured.text || '' });
            } else if (data.error) {
                renderErrorMessage(data.error);
            } else {
                renderMessage({ role: 'ai', content: 'No response.' });
            }

        } catch (err) {
            hideTyping();
            setSendingState(false);
            renderErrorMessage('Connection error. Please check your network and try again.');
        }
    }

    function setSendingState(sending) {
        if (input) input.disabled = sending;
        if (sendBtn) {
            sendBtn.disabled = sending;
            sendBtn.classList.toggle('is-loading', sending);
        }
    }

    function renderErrorMessage(text) {
        renderMessage({
            role: 'ai',
            content: text,
            structured: { type: 'text', text },
        });
    }

    /* ============================= CONFIRMATION MODAL ============================= */
    function openConfirmModal(action) {
        if (!confirmModal) return;

        pendingAction = action || null;

        if (confirmText) {
            confirmText.textContent = action?.description
                || 'Are you sure you want to proceed?';
        }

        if (confirmMeta && action?.details) {
            confirmMeta.innerHTML = '';
            Object.entries(action.details).forEach(([k, v]) => {
                const row = document.createElement('div');
                row.className = 'confirm-meta-row';
                const kEl = document.createElement('span');
                kEl.className = 'confirm-meta-key';
                kEl.textContent = k;
                const vEl = document.createElement('span');
                vEl.className = 'confirm-meta-value';
                vEl.textContent = v;
                row.appendChild(kEl);
                row.appendChild(vEl);
                confirmMeta.appendChild(row);
            });
        } else if (confirmMeta) {
            confirmMeta.innerHTML = '';
        }

        confirmModal.hidden = false;
        confirmModal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';

        setTimeout(() => confirmApprove?.focus(), 50);
    }

    function closeConfirmModal() {
        if (!confirmModal) return;
        confirmModal.hidden = true;
        confirmModal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        pendingAction = null;
    }

    async function approveAction() {
        if (!pendingAction) {
            closeConfirmModal();
            return;
        }

        const action = pendingAction;

        if (confirmApprove) {
            confirmApprove.disabled = true;
            confirmApprove.classList.add('is-loading');
        }

        try {
            const response = await fetch(ACTION_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({
                    action_type: action.type,
                    params: action.params || {},
                }),
            });

            const data = await response.json().catch(() => ({}));

            closeConfirmModal();

            if (response.ok && data.success) {
                renderMessage({
                    role: 'ai',
                    content: '✓ ' + (data.message || 'Action completed successfully.'),
                });
            } else {
                renderErrorMessage(
                    data.error || 'The action could not be completed.'
                );
            }

        } catch (err) {
            closeConfirmModal();
            renderErrorMessage('Connection error. The action was not executed.');
        } finally {
            if (confirmApprove) {
                confirmApprove.disabled = false;
                confirmApprove.classList.remove('is-loading');
            }
        }
    }

    if (confirmApprove) {
        confirmApprove.addEventListener('click', approveAction);
    }

    confirmCancel.forEach((btn) => {
        btn.addEventListener('click', closeConfirmModal);
    });

    if (confirmModal) {
        confirmModal.addEventListener('click', (e) => {
            if (e.target === confirmModal) closeConfirmModal();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && confirmModal && !confirmModal.hidden) {
            closeConfirmModal();
        }
    });

    /* ============================= FORM SUBMIT ============================= */
    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            sendMessage(input?.value || '');
        });
    }

    /* ============================= INPUT KEYBOARD ============================= */
    if (input) {
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                form?.dispatchEvent(new Event('submit', { cancelable: true }));
            }
        });

        // auto-resize
        input.addEventListener('input', function () {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        });
    }

    /* ============================= SUGGESTED PROMPTS ============================= */
    suggestions.forEach((chip) => {
        chip.addEventListener('click', function () {
            const prompt = chip.dataset.prompt;
            if (prompt) {
                sendMessage(prompt);
            }
        });
    });

    /* ============================= RETRY ============================= */
    if (retryBtn) {
        retryBtn.addEventListener('click', function () {
            if (!lastUserMessage) return;
            sendMessage(lastUserMessage, { retry: true });
        });
    }

    /* ============================= CLEAR CONVERSATION ============================= */
    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            if (!confirm('Clear the current conversation?')) return;

            // احتفظ برسالة الترحيب الأولى فقط
            const messages = conversation.querySelectorAll('.chat-message');
            messages.forEach((m, i) => {
                if (i > 0) m.remove();
            });

            conversationHistory = [];
            lastUserMessage = null;
        });
    }

    /* ============================= NEW CONVERSATION ============================= */
    if (newBtn) {
        newBtn.addEventListener('click', function () {
            if (!confirm('Start a new conversation? This will clear the current one.')) return;

            const messages = conversation.querySelectorAll('.chat-message');
            messages.forEach((m, i) => {
                if (i > 0) m.remove();
            });

            conversationHistory = [];
            lastUserMessage = null;

            // رسالة ترحيب جديدة
            renderMessage({
                role: 'ai',
                content: 'New conversation started. How can I help you?',
            });
        });
    }

    /* ============================= INITIAL FOCUS ============================= */
    if (input) {
        setTimeout(() => input.focus({ preventScroll: true }), 200);
    }
})();