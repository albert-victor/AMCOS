/**
 * AMCOS pay simulation — compact success card + view receipt / OK.
 */
(function () {
    'use strict';

    function el(id) { return document.getElementById(id); }

    function lang() {
        var h = document.documentElement.lang || 'sw';
        return h.indexOf('en') === 0 ? 'en' : 'sw';
    }

    function msg(sw, en) { return lang() === 'en' ? en : sw; }

    function esc(s) {
        var d = document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    }

    function formatAmount(amount) {
        var n = Number(amount || 0);
        return n.toLocaleString(lang() === 'en' ? 'en-TZ' : 'sw-TZ', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        });
    }

    var overlay, proc, succ, summary, hint, btnOk, btnView;
    var exitUrl = '';
    var receiptUrl = '';
    var isSubmitting = false;

    function buildMiniCard(data) {
        var amount = formatAmount(data.amount);
        var ref = data.reference_number || '—';
        var receipt = data.receipt_number || '';
        var method = data.payment_method_label || '';

        var html =
            '<div class="pay-sim-mini-amount">TZS ' + esc(amount) + '</div>' +
            '<div class="pay-sim-mini-rows">' +
            '<div class="pay-sim-mini-row"><span>' + msg('Rejea', 'Reference') + '</span><strong>' + esc(ref) + '</strong></div>';

        if (receipt) {
            html += '<div class="pay-sim-mini-row"><span>' + msg('Stakabadhi', 'Receipt') + '</span><strong>' + esc(receipt) + '</strong></div>';
        }
        if (method) {
            html += '<div class="pay-sim-mini-row"><span>' + msg('Njia', 'Method') + '</span><strong>' + esc(method) + '</strong></div>';
        }

        html += '</div>';
        return html;
    }

    function initOverlay() {
        overlay = el('paySimOverlay');
        if (!overlay) return false;
        proc = el('paySimProcessing');
        succ = el('paySimSuccess');
        summary = el('paySimReceiptSummary');
        hint = el('paySimExtraHint');
        btnOk = el('paySimBtnOk');
        btnView = el('paySimBtnView');
        if (btnOk) btnOk.addEventListener('click', onOk);
        if (btnView) btnView.addEventListener('click', onViewReceipt);
        return true;
    }

    function resetOverlay() {
        if (!overlay) return;
        overlay.classList.remove('active');
        overlay.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('pay-sim-open');
        if (proc) proc.hidden = false;
        if (succ) { succ.hidden = true; succ.classList.remove('is-visible'); }
        if (hint) hint.hidden = true;
    }

    function showProcessing() {
        if (!overlay) return;
        document.body.classList.add('pay-sim-open');
        overlay.classList.add('active');
        overlay.setAttribute('aria-hidden', 'false');
        if (proc) proc.hidden = false;
        if (succ) { succ.hidden = true; succ.classList.remove('is-visible'); }
    }

    function showSuccess(data) {
        if (!proc) return;
        proc.hidden = true;
        if (succ) {
            succ.hidden = false;
            requestAnimationFrame(function () { succ.classList.add('is-visible'); });
        }
        if (summary && data) {
            summary.innerHTML = buildMiniCard(data);
        }
        if (hint && data.new_total_shares != null) {
            hint.hidden = false;
            if (data.purchased_for) {
                hint.textContent = msg(
                    'Hisa za ' + data.purchased_for + ' sasa: ' + data.new_total_shares,
                    data.purchased_for + '\'s shares now: ' + data.new_total_shares
                );
            } else {
                hint.textContent = msg(
                    'Hisa zako sasa: ' + data.new_total_shares,
                    'Your shares now: ' + data.new_total_shares
                );
            }
        } else if (hint) {
            hint.hidden = true;
        }
        receiptUrl = data.receipt_url || '';
        var target = data.redirect_url || data.list_url || window.location.pathname;
        exitUrl = target + (target.indexOf('?') >= 0 ? '&' : '?') + '_=' + Date.now();
        if (btnView) btnView.disabled = !receiptUrl;
    }

    function onOk() {
        window.location.replace(exitUrl || '/dashboard/');
    }

    function onViewReceipt() {
        if (!receiptUrl) return;
        window.open(receiptUrl, '_blank', 'noopener');
    }

    function bindForm(form) {
        if (!form || form.dataset.paySimBound === '1') return;
        form.dataset.paySimBound = '1';
        form.addEventListener('submit', function (e) { e.preventDefault(); });

        var payBtn = form.querySelector('[data-pay-sim-submit]');
        if (!payBtn) return;

        payBtn.addEventListener('click', function (e) {
            e.preventDefault();
            if (isSubmitting) return;

            if (typeof validatePaymentMethodOther === 'function' && !validatePaymentMethodOther(form)) {
                return;
            }

            var phone = form.querySelector('[name="phone"], [name="payment_phone"]');
            var method = form.querySelector('[name="payment_method"]');
            if (phone && !phone.value.trim()) {
                alert(msg('Weka namba ya simu.', 'Enter phone number.'));
                phone.focus();
                return;
            }
            if (method && method.required && !method.value) {
                alert(msg('Chagua njia ya malipo.', 'Select payment method.'));
                method.focus();
                return;
            }

            var required = form.querySelectorAll('[required]');
            for (var i = 0; i < required.length; i++) {
                if (required[i].name === 'transaction_id') continue;
                if (!required[i].value || (required[i].type === 'radio' && !form.querySelector('[name="' + required[i].name + '"]:checked'))) {
                    if (required[i].offsetParent !== null) {
                        alert(msg('Jaza sehemu zote zinazohitajika.', 'Fill all required fields.'));
                        required[i].focus();
                        return;
                    }
                }
            }

            isSubmitting = true;
            showProcessing();

            var fd = new FormData(form);
            fd.set('pay_simulation', '1');

            fetch(form.action || window.location.href, {
                method: 'POST',
                body: fd,
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            })
                .then(function (res) {
                    var ct = res.headers.get('content-type') || '';
                    if (ct.indexOf('application/json') !== -1) {
                        return res.json().then(function (data) {
                            if (data.success) {
                                showSuccess(data);
                            } else {
                                resetOverlay();
                                alert(data.error || msg('Malipo yameshindwa.', 'Payment failed.'));
                            }
                            isSubmitting = false;
                        });
                    }
                    return res.text().then(function (html) {
                        resetOverlay();
                        isSubmitting = false;
                        if (res.redirected && res.url) {
                            window.location.href = res.url;
                            return;
                        }
                        var doc = new DOMParser().parseFromString(html, 'text/html');
                        var alerts = doc.querySelectorAll('.alert');
                        if (alerts.length) {
                            var card = form.closest('.card-body') || form.parentElement;
                            card.querySelectorAll('.alert').forEach(function (a) { a.remove(); });
                            alerts.forEach(function (a) {
                                card.insertBefore(a.cloneNode(true), card.firstChild);
                            });
                        } else {
                            alert(msg('Hitilafu. Jaribu tena.', 'Error. Please try again.'));
                        }
                    });
                })
                .catch(function () {
                    resetOverlay();
                    isSubmitting = false;
                    alert(msg('Hitilafu ya mtandao.', 'Network error.'));
                });
        });
    }

    function init() {
        if (!initOverlay()) return;
        document.querySelectorAll('form.pay-sim-form').forEach(bindForm);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
