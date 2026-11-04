import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def emails_url():
    return os.environ.get(
        'EMAILS_API_URL',
        'http://127.0.0.1:8000/api/v1/emails'
    ).strip().rstrip('/')


def read_json(url):
    request = Request(url, headers={'Accept': 'application/json'})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def get_emails():
    url = emails_url()
    if not url:
        return [], 'E-posta API adresi ayarlanmamış.'
    try:
        data = read_json(url)
        if not isinstance(data, list):
            raise ValueError('Liste yanıtı JSON listesi olmalı.')
        for item in data:
            if not isinstance(item, dict):
                raise ValueError('Geçersiz e-posta kaydı.')
            identity = item.get('email_id', item.get('id', item.get('source_email_id')))
            if identity is None or isinstance(identity, (dict, list, bool)):
                raise ValueError('E-posta kimliği eksik veya geçersiz.')

            # The DB API returns category fields flat; the inbox UI consumes
            # the same nested shape produced by the analysis API.
            detail, _, _ = get_email(identity)
            if detail:
                item.update(detail)

            tags = item.get('tags') or []
            item['classification'] = {
                'primary_category': item.get('primary_category'),
                'email_type': item.get('email_type'),
                'tags': [
                    tag.get('name', '') if isinstance(tag, dict) else str(tag)
                    for tag in tags
                ],
            }
            item.setdefault('tasks', [])
            item.setdefault('events', [])
            item.setdefault('evidence', [])
        return data, None
    except (URLError, OSError, ValueError, TypeError):
        return [], 'E-postalar alınamadı. API bağlantısını ve yanıt biçimini kontrol edin.'


def get_email(email_id):
    url = emails_url()
    if not url:
        return None, 'E-posta API adresi ayarlanmamış.', 503
    try:
        data = read_json(f'{url}/{quote(str(email_id), safe="")}')
        if not isinstance(data, dict):
            raise ValueError('Detay yanıtı JSON nesnesi olmalı.')
        for name in ('tasks', 'events', 'evidence'):
            values = data.get(name, [])
            if not isinstance(values, list) or not all(isinstance(v, dict) for v in values):
                raise ValueError('Detay alanları geçersiz.')
        if not isinstance(data.get('classification', {}), dict):
            raise ValueError('Kategori alanı geçersiz.')
        return data, None, 200
    except HTTPError as error:
        if error.code == 404:
            return None, 'E-posta ayrıntısı bulunamadı.', 404
        return None, 'Veritabanı servisi ayrıntı isteğine hata döndürdü.', 502
    except (URLError, OSError, ValueError, TypeError):
        return None, 'E-posta ayrıntısı alınamadı. Bağlantıyı veya yanıt biçimini kontrol edin.', 502
