import os
import requests

ACLED_TOKEN_URL = 'https://acleddata.com/oauth/token'
ACLED_CLIENT_ID = 'acled'

from dotenv import load_dotenv

# Load cấu hình từ file .env hiện tại
load_dotenv()

def get_acled_token(user_agent=None):
    """
    Obtain a valid ACLED access token.

    Priority:
      1. ACLED_EMAIL + ACLED_PASSWORD: OAuth exchange
      2. ACLED_ACCESS_TOKEN: static token (legacy, expires 24h)
      3. Neither: None

    Args:
        user_agent (str, optional): User-Agent header value.

    Returns:
        str | None: The access token or None if unavailable.
    """
    email = os.environ.get('ACLED_EMAIL', '').strip()
    password = os.environ.get('ACLED_PASSWORD', '').strip()

    if email and password:
        print('  ACLED: exchanging credentials for OAuth token...')
        
        payload = {
            'username': email,
            'password': password,
            'grant_type': 'password',
            'client_id': ACLED_CLIENT_ID,
        }

        headers = {}
        if user_agent:
            headers['User-Agent'] = user_agent

        try:
            # requests.post with 'data' param automatically sets 
            # Content-Type to application/x-www-form-urlencoded
            resp = requests.post(
                ACLED_TOKEN_URL,
                data=payload,
                headers=headers,
                timeout=15
            )

            if not resp.ok:
                print(f"  ACLED OAuth exchange failed ({resp.status_code}): {resp.text[:200]}")
                # Fall through to static token check
            else:
                data = resp.json()
                if 'access_token' in data:
                    print('  ACLED: OAuth token obtained successfully')
                    return data['access_token']
                print('  ACLED: OAuth response missing access_token')
                
        except requests.exceptions.RequestException as e:
            print(f"  ACLED: Request failed: {e}")
            # Fall through to static token check

    static_token = os.environ.get('ACLED_ACCESS_TOKEN', '').strip()
    if static_token:
        print('  ACLED: using static ACLED_ACCESS_TOKEN (expires after 24h)')
        return static_token

    return None


if __name__ == '__main__':
    acled_token = get_acled_token()
    print(f'ACLED_TOKEN={acled_token}' if acled_token else 'No ACLED token available.')