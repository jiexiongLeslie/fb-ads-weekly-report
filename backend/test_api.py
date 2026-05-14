import json
from datetime import date, timedelta

import requests


BASE_URL = 'http://localhost:5003'


def print_response(title, response):
    print(f'\n{title}')
    print(f'Status: {response.status_code}')
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except ValueError:
        print(response.text)


print('=== API smoke test ===')

token_resp = requests.get(f'{BASE_URL}/api/token-status', timeout=20)
print_response('1. Token status', token_resp)

end_date = date.today()
start_date = end_date - timedelta(days=7)
sync_resp = requests.post(
    f'{BASE_URL}/api/sync',
    json={
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'force_refresh_days': 0,
    },
    timeout=300,
)
print_response('2. Sync last 7 days', sync_resp)

print('\n=== Done ===')
