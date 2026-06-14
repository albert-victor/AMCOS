/**
 * Auth pages — placeholders & select prompts follow language toggle (KISW / ENG)
 */
function applyAuthI18n(lang) {
    lang = lang || document.documentElement.getAttribute('lang') || 'en';

    document.querySelectorAll('[data-ph-sw]').forEach(function (el) {
        var text = lang === 'en' ? el.getAttribute('data-ph-en') : el.getAttribute('data-ph-sw');
        if (text !== null && 'placeholder' in el) {
            el.placeholder = text;
        }
    });

    document.querySelectorAll('select[data-opt-sw]').forEach(function (sel) {
        var empty = sel.querySelector('option[value=""]');
        if (empty) {
            empty.textContent = lang === 'en'
                ? sel.getAttribute('data-opt-en')
                : sel.getAttribute('data-opt-sw');
        }
    });

    document.querySelectorAll('option[data-label-sw]').forEach(function (opt) {
        var label = lang === 'en' ? opt.getAttribute('data-label-en') : opt.getAttribute('data-label-sw');
        if (label) opt.textContent = label;
    });
}

document.addEventListener('DOMContentLoaded', function () {
    applyAuthI18n();
});
