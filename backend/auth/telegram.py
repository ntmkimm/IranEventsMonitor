#!/usr/bin/env python3
"""
Generate a TELEGRAM_SESSION (StringSession) for the Railway Telegram OSINT poller.

Usage (local only):
  pip install telethon
  TELEGRAM_API_ID=... TELEGRAM_API_HASH=... python telegram_session_auth.py

Output:
  Prints TELEGRAM_SESSION=... to stdout.
"""

import os
import sys
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

from dotenv import load_dotenv

# Load cấu hình từ file .env hiện tại
load_dotenv()

def main():
    api_id_str = os.environ.get('TELEGRAM_API_ID', '')
    api_hash = os.environ.get('TELEGRAM_API_HASH', '')

    if not api_id_str or not api_hash:
        print('Missing TELEGRAM_API_ID or TELEGRAM_API_HASH. Get them from https://my.telegram.org/apps', file=sys.stderr)
        sys.exit(1)

    try:
        api_id = int(api_id_str)
    except ValueError:
        print('TELEGRAM_API_ID must be a number.', file=sys.stderr)
        sys.exit(1)

    try:
        # Prompt for details beforehand (matching the JS script's behavior)
        phone_number = input('Phone number (with country code, e.g. +971...): ').strip()
        password = input('2FA password (press enter if none): ').strip()

        # Initialize the Telegram Client with an empty StringSession
        client = TelegramClient(StringSession(), api_id, api_hash)

        # client.start() automatically handles the auth flow
        client.start(
            phone=phone_number,
            password=password if password else None,
            code_callback=lambda: input('Verification code from Telegram: ').strip()
        )

        # Export the session string
        session = client.session.save()
        print('\n✅ Generated session. Add this as a Railway secret:')
        print(f'TELEGRAM_SESSION={session}')

    except KeyboardInterrupt:
        print('\nAborted.')
        sys.exit(0)
    except Exception as e:
        print(f'\nError: {e}', file=sys.stderr)
        sys.exit(1)
    finally:
        if 'client' in locals() and client.is_connected():
            client.disconnect()

if __name__ == '__main__':
    main()