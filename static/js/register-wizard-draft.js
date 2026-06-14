/**
 * Persist registration wizard step + form fields when visiting terms page.
 */
(function (global) {
    var DRAFT_KEY = 'mgowelo_reg_wizard_v1';
    var SKIP_NAMES = { csrfmiddlewaretoken: true };

    function getForm() {
        return document.getElementById('registerForm');
    }

    function saveDraft(step) {
        var form = getForm();
        if (!form) return;
        var data = { step: step || 1, fields: {} };
        form.querySelectorAll('input, select, textarea').forEach(function (el) {
            var name = el.name;
            if (!name || SKIP_NAMES[name]) return;
            if (el.type === 'password') {
                data.fields[name] = el.value;
                return;
            }
            if (el.type === 'checkbox' || el.type === 'radio') {
                if (el.type === 'checkbox') data.fields[name] = el.checked;
                else if (el.checked) data.fields[name] = el.value;
            } else {
                data.fields[name] = el.value;
            }
        });
        try {
            sessionStorage.setItem(DRAFT_KEY, JSON.stringify(data));
        } catch (e) { /* quota */ }
    }

    function loadDraft() {
        var form = getForm();
        if (!form) return null;
        var raw;
        try {
            raw = sessionStorage.getItem(DRAFT_KEY);
        } catch (e) {
            return null;
        }
        if (!raw) return null;
        try {
            return JSON.parse(raw);
        } catch (e) {
            return null;
        }
    }

    function applyDraft(draft) {
        var form = getForm();
        if (!form || !draft || !draft.fields) return draft.step || 1;
        Object.keys(draft.fields).forEach(function (name) {
            var el = form.elements[name];
            if (!el) return;
            var val = draft.fields[name];
            if (el.type === 'checkbox') {
                el.checked = !!val;
            } else if (el.type === 'radio') {
                var radios = form.querySelectorAll('input[name="' + name + '"]');
                radios.forEach(function (r) { r.checked = r.value === val; });
            } else {
                el.value = val == null ? '' : val;
            }
        });
        var hectaresSelect = document.getElementById('hectaresSelect');
        var hectaresOther = document.getElementById('hectaresOther');
        if (hectaresSelect && hectaresOther && hectaresSelect.value === 'other') {
            hectaresOther.hidden = false;
            hectaresOther.setAttribute('required', 'required');
        }
        if (typeof initPaymentMethodOther === 'function') {
            initPaymentMethodOther(form);
        }
        return Math.min(Math.max(parseInt(draft.step, 10) || 1, 1), 3);
    }

    function clearDraft() {
        try {
            sessionStorage.removeItem(DRAFT_KEY);
        } catch (e) { /* ignore */ }
    }

    function bindTermsLink(saveFn) {
        var link = document.getElementById('termsLink');
        if (!link) return;
        link.addEventListener('click', function (e) {
            e.stopPropagation();
            if (typeof saveFn === 'function') saveFn();
            else saveDraft(3);
        });
    }

    global.MgoweloRegDraft = {
        save: saveDraft,
        load: loadDraft,
        apply: applyDraft,
        clear: clearDraft,
        bindTermsLink: bindTermsLink,
    };
})(window);
