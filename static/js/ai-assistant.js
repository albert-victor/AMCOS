/**
 * AMCOS AI — OpenRouter-backed chat with typewriter effect.
 */
(function () {
    'use strict';

    var aiOpen = false;
    var typingInProgress = false;

    function el(id) {
        return document.getElementById(id);
    }

    function currentLang() {
        var htmlLang = document.documentElement.lang || 'sw';
        return htmlLang.indexOf('en') === 0 ? 'en' : 'sw';
    }

    function nowTime() {
        return new Date().toLocaleTimeString(currentLang() === 'en' ? 'en-TZ' : 'sw-TZ', {
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function scrollMessages() {
        var msgs = el('aiMessages');
        if (msgs) {
            msgs.scrollTop = msgs.scrollHeight;
        }
    }

    function escapeHtml(text) {
        var d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }

    function getCsrfToken() {
        var input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input) {
            return input.value;
        }
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    window.toggleAI = function () {
        if (aiOpen) {
            window.closeAI();
        } else {
            window.openAI();
        }
    };

    window.openAI = function () {
        aiOpen = true;
        var panel = el('aiPanel');
        var overlay = el('aiOverlay');
        var btn = el('aiBtn');
        if (panel) panel.classList.add('open');
        if (overlay) overlay.classList.add('open');
        if (btn) btn.classList.add('is-hidden');
        var input = el('aiInput');
        if (input) {
            setTimeout(function () { input.focus(); }, 350);
        }
    };

    window.closeAI = function () {
        aiOpen = false;
        var panel = el('aiPanel');
        var overlay = el('aiOverlay');
        var btn = el('aiBtn');
        if (panel) panel.classList.remove('open');
        if (overlay) overlay.classList.remove('open');
        if (btn) btn.classList.remove('is-hidden');
    };

    window.askAI = function (q) {
        var input = el('aiInput');
        if (input) {
            input.value = q;
        }
        window.sendAI();
    };

    function showTypingIndicator() {
        removeTypingIndicator();
        var msgs = el('aiMessages');
        if (!msgs) return;

        var wrap = document.createElement('div');
        wrap.className = 'ai-typing-wrap';
        wrap.id = 'aiTyping';
        wrap.innerHTML =
            '<div class="ai-typing" aria-hidden="true">' +
            '<span></span><span></span><span></span>' +
            '</div>' +
            '<span class="ai-typing-label">' +
            (currentLang() === 'en' ? 'AMCOS AI is typing' : 'AMCOS AI inaandika') +
            '<span class="ai-typewriter-cursor" aria-hidden="true"></span></span>';
        msgs.appendChild(wrap);
        scrollMessages();
    }

    function removeTypingIndicator() {
        var t = el('aiTyping');
        if (t) t.remove();
    }

    function typewriterInto(element, text, done) {
        var speed = 14;
        var i = 0;
        element.textContent = '';
        typingInProgress = true;

        function tick() {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i += 1;
                scrollMessages();
                setTimeout(tick, speed);
            } else {
                typingInProgress = false;
                if (done) done();
            }
        }
        tick();
    }

    function appendBotMessage(text) {
        var msgs = el('aiMessages');
        if (!msgs) return;

        var botDiv = document.createElement('div');
        botDiv.className = 'ai-msg bot';
        var icon = document.createElement('i');
        icon.className = 'fa-solid fa-comments';
        icon.setAttribute('aria-hidden', 'true');

        var textSpan = document.createElement('span');
        textSpan.className = 'ai-msg-body';

        var timeSpan = document.createElement('span');
        timeSpan.className = 'time';
        timeSpan.textContent = nowTime();

        botDiv.appendChild(icon);
        botDiv.appendChild(textSpan);
        botDiv.appendChild(timeSpan);
        msgs.appendChild(botDiv);
        scrollMessages();

        typewriterInto(textSpan, text, function () {
            scrollMessages();
        });
    }

    function appendUserMessage(text) {
        var msgs = el('aiMessages');
        if (!msgs) return;

        var userDiv = document.createElement('div');
        userDiv.className = 'ai-msg user';
        userDiv.textContent = text;

        var timeSpan = document.createElement('span');
        timeSpan.className = 'time';
        timeSpan.textContent = nowTime();
        userDiv.appendChild(timeSpan);

        msgs.appendChild(userDiv);
        scrollMessages();
    }

    window.sendAI = function () {
        if (typingInProgress) return;

        var input = el('aiInput');
        var sendBtn = el('aiSendBtn');
        if (!input) return;

        var question = input.value.trim();
        if (!question) return;

        input.value = '';
        appendUserMessage(question);

        if (sendBtn) sendBtn.disabled = true;
        showTypingIndicator();

        fetch('/chatbot/api/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                question: question,
                lang: currentLang(),
            }),
        })
            .then(function (r) {
                return r.json().then(function (data) {
                    if (!r.ok) {
                        throw new Error(data.error || 'request failed');
                    }
                    return data;
                });
            })
            .then(function (data) {
                removeTypingIndicator();
                var answer = data.answer || (
                    currentLang() === 'en'
                        ? 'Sorry, I could not answer that. Please try again.'
                        : 'Samahani, sikupata jibu. Tafadhali jaribu tena.'
                );
                appendBotMessage(answer);
                if (sendBtn) sendBtn.disabled = false;
            })
            .catch(function () {
                removeTypingIndicator();
                appendBotMessage(
                    currentLang() === 'en'
                        ? 'Network error. Please check your connection and try again.'
                        : 'Tatizo la mtandao. Angalia muunganisho na ujaribu tena.'
                );
                if (sendBtn) sendBtn.disabled = false;
            });
    };

    document.addEventListener('DOMContentLoaded', function () {
        var input = el('aiInput');
        if (input) {
            input.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    window.sendAI();
                }
            });
        }
    });
})();
