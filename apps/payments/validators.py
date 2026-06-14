"""Shared payment form validation helpers."""


def payment_method_other_required(payment_method, other_text):
    if payment_method != 'other':
        return True
    return bool((other_text or '').strip())


def payment_method_other_message(lang='en'):
    if lang == 'en':
        return 'Please specify the payment method.'
    return 'Tafadhali eleza njia ya malipo.'


def append_method_specify(description, payment_method, other_text):
    other_text = (other_text or '').strip()
    if payment_method == 'other' and other_text:
        note = f'Payment method: {other_text}'
        if description:
            return f'{description} | {note}'
        return note
    return description or ''
