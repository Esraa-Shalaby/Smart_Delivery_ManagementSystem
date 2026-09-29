/* ============================================================
   chatbot.js
   Floating AI chat window
   ============================================================ */
(function () {
    'use strict';

    const root = document.querySelector('[data-chatbot]');
    if (!root) return;

    const trigger = root.querySelector('[data-chatbot-trigger]');
    const window_ = root.querySelector('[data-chatbot-window]');
    const conversation = root.querySelector('[data-chatbot-conversation]');
    const form = root.querySelector('[data-chatbot-form]');
    const input = root.querySelector('[data-chatbot-input]');
    const typing = root.querySelector('[data-chatbot-typing]');
    const closeBtn = root.querySelector('[data-chatbot-action="close"]');
    const clearBtn = root.querySelector('[data-chatbot-action="clear"]');
    const chips = root.querySelectorAll('[data-chatbot-prompt]');

    // endpoint يأتي من data-attribute
    const endpoint = root.dataset.chatbotEndpoint || null;

    /* ============================= OPEN / CLOSE ============================= */
    function open() {
        window_.hidden = false;
        trigger.setAttribute('aria-expanded', 'true');
        if (input) setTimeout(() => input.focus(), 50);
        scrollToBottom();
    }

    function close() {
        window_.hidden = true;
        trigger.setAttribute('aria-expanded', 'false');
        trigger.focus();
    }

    if (trigger) {
        trigger.addEventListener('click', function () {
            if (window_.hidden) open();
            else close();
        });
    }

    if (closeBtn) closeBtn.addEventListener('click', close);

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && !window_.hidden) close();
    });

    /* ============================= SCROLL ============================= */
    function scrollToBottom() {
        if (conversation) {
            conversation.scrollTop = conversation.scrollHeight;
        }
    }

    /* ============================= MESSAGE RENDERING ============================= */
    function getTime() {
        const d = new Date();
        return String(d.getHours()).padStart(2, '0') + ':' +
            String(d.getMinutes()).padStart(2, '0');
    }

    function addMessage(author, content, isUser) {
        const msg = document.createElement('div');
        msg.className = 'app-chatbot-msg' + (isUser ? ' app-chatbot-msg-user' : ' app-chatbot-msg-ai');

        const avatar = document.createElement('div');
        avatar.className = 'app-chatbot-msg-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.textContent = isUser ? 'U' : '✦';

        const bubble = document.createElement('div');
        bubble.className = 'app-chatbot-bubble';

        const head = document.createElement('div');
        head.className = 'app-chatbot-bubble-head';

        const author_ = document.createElement('span');
        author_.className = 'app-chatbot-author';
        author_.textContent = author;

        const time = document.createElement('span');
        time.className = 'app-chatbot-time';
        time.textContent = getTime();

        head.appendChild(author_);
        head.appendChild(time);

        const content_ = document.createElement('div');
        content_.className = 'app-chatbot-content';
        content_.textContent = content;

        bubble.appendChild(head);
        bubble.appendChild(content_);
        msg.appendChild(avatar);
        msg.appendChild(bubble);
        conversation.appendChild(msg);
        scrollToBottom();
    }

    function showTyping() {
        if (typing) typing.hidden = false;
        scrollToBottom();
    }

    function hideTyping() {
        if (typing) typing.hidden = true;
    }

    /* ============================= SEND MESSAGE ============================= */
    async function sendMessage(text) {
        if (!text.trim()) return;

        addMessage('You', text, true);
        input.value = '';
        input.style.height = 'auto';

        if (!endpoint) {
            addMessage('AI Assistant', 'AI assistant is not configured.', false);
            return;
        }

        showTyping();

        try {
            const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({ message: text }),
            });

            hideTyping();

            if (!response.ok) {
                addMessage('AI Assistant', 'Sorry, something went wrong. Please try again.', false);
                return;
            }

            const data = await response.json();
            const reply = data.reply || data.message || 'No response.';
            addMessage('AI Assistant', reply, false);
        } catch (err) {
            hideTyping();
            addMessage('AI Assistant', 'Connection error. Please try again.', false);
        }
    }

    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            sendMessage(input.value);
        });
    }

    /* ============================= KEYBOARD ============================= */
    if (input) {
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                form.dispatchEvent(new Event('submit'));
            }
        });
    }

    /* ============================= SUGGESTIONS ============================= */
    chips.forEach((chip) => {
        chip.addEventListener('click', function () {
            const prompt = chip.dataset.chatbotPrompt;
            if (prompt) {
                input.value = prompt;
                form.dispatchEvent(new Event('submit'));
            }
        });
    });

    /* ============================= CLEAR ============================= */
    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            if (!confirm('Clear conversation?')) return;
            const messages = conversation.querySelectorAll('.app-chatbot-msg');
            messages.forEach((m, i) => {
                if (i > 0) m.remove(); // إبقاء أول رسالة ترحيب
            });
        });
    }
})();