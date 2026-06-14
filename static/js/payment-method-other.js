/**
 * Show "please specify" when payment method is "other".
 */
function initPaymentMethodOther(root) {
    root = root || document;
    var sel = root.querySelector('select[name="payment_method"]');
    var wrap = root.querySelector('#paymentMethodOtherWrap');
    var inp = root.querySelector('[name="payment_method_other"]');
    if (!sel || !wrap || !inp) return;

    function toggle() {
        var isOther = sel.value === 'other';
        wrap.hidden = !isOther;
        inp.required = isOther;
        if (!isOther) {
            inp.value = '';
            inp.classList.remove('error');
        }
    }

    sel.addEventListener('change', toggle);
    toggle();
}

function validatePaymentMethodOther(root) {
    root = root || document;
    var sel = root.querySelector('select[name="payment_method"]');
    var inp = root.querySelector('[name="payment_method_other"]');
    if (!sel || sel.value !== 'other') return true;
    if (inp && inp.value.trim()) {
        inp.classList.remove('error');
        return true;
    }
    if (inp) inp.classList.add('error');
    var lang = (document.documentElement.lang || 'en').toLowerCase();
    alert(lang === 'en'
        ? 'Please specify the payment method.'
        : 'Tafadhali eleza njia ya malipo.');
    return false;
}

document.addEventListener('DOMContentLoaded', function () {
    initPaymentMethodOther(document);
});
