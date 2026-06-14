"""Quick ngrok login probe (run: python scripts/test_ngrok_login.py)."""
import re
import urllib.parse
import urllib.request
import http.cookiejar

BASE = 'https://preacher-scarf-postbox.ngrok-free.dev'
USER = 'amcos001_parrc'
PWD = 'chair123'


def main():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    headers = {'ngrok-skip-browser-warning': '1'}

    r1 = opener.open(urllib.request.Request(BASE + '/auth/login/', headers=headers), timeout=20)
    html = r1.read().decode('utf-8', errors='replace')
    print('GET', r1.status, 'len', len(html))
    print('is_ngrok_interstitial', 'ngrok' in html[:2000].lower() and 'csrfmiddlewaretoken' not in html)
    print('is_django_login', 'auth-form' in html or 'csrfmiddlewaretoken' in html)
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    form_csrf = m.group(1) if m else ''
    cookie_csrf = next((c.value for c in cj if c.name == 'csrftoken'), '')
    print('csrf form/cookie match:', form_csrf == cookie_csrf, bool(form_csrf))

    token = form_csrf or cookie_csrf
    data = urllib.parse.urlencode({
        'username': USER,
        'password': PWD,
        'csrfmiddlewaretoken': token,
    }).encode()
    req2 = urllib.request.Request(
        BASE + '/auth/login/',
        data=data,
        headers={**headers, 'Referer': BASE + '/auth/login/'},
        method='POST',
    )
    try:
        r2 = opener.open(req2, timeout=20)
        body = r2.read().decode('utf-8', errors='replace')
        print('POST', r2.status, 'url', r2.geturl())
        print('sessionid', any(c.name == 'sessionid' for c in cj))
        if 'Invalid credentials' in body:
            print('RESULT: Invalid credentials')
        elif '/dashboard' in r2.geturl():
            print('RESULT: OK redirect dashboard')
    except urllib.error.HTTPError as e:
        print('POST HTTP', e.code)
        print(e.read()[:600].decode(errors='replace'))


def probe(base, use_ngrok_header=False):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    headers = {'ngrok-skip-browser-warning': '1'} if use_ngrok_header else {}
    html = opener.open(
        urllib.request.Request(base + '/auth/login/', headers=headers), timeout=20,
    ).read().decode('utf-8', errors='replace')
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    form_csrf = m.group(1) if m else ''
    cookie_csrf = next((c.value for c in cj if c.name == 'csrftoken'), '')
    token = form_csrf or cookie_csrf  # must use hidden input value, not raw cookie
    data = urllib.parse.urlencode({
        'username': USER, 'password': PWD, 'csrfmiddlewaretoken': token,
    }).encode()
    req2 = urllib.request.Request(
        base + '/auth/login/', data=data,
        headers={**headers, 'Referer': base + '/auth/login/'}, method='POST',
    )
    r2 = opener.open(req2, timeout=20)
    ok = any(c.name == 'sessionid' for c in cj)
    body = r2.read().decode('utf-8', errors='replace')
    return {
        'csrf_match': form_csrf == cookie_csrf,
        'session': ok,
        'invalid': 'Invalid credentials' in body,
        'url': r2.geturl(),
    }


if __name__ == '__main__':
    main()
    print('--- compare ---')
    for label, url, hdr in [
        ('local', 'http://127.0.0.1:8000', False),
        ('ngrok', BASE, True),
    ]:
        print(label, probe(url, hdr))
