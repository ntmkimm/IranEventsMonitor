import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import AuthKeyDuplicatedError, FloodWaitError

# Force UTF-8 for Windows terminal compatibility
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# --- Configuration & Paths ---
load_dotenv()

# Get the absolute path of the backend directory
# Current file is in /backend/crawlers/, so parent is /backend/
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "data" / "telegram-channels.json"
OUTPUT_FILE = BASE_DIR / "data" / "telegram_results.json"

API_ID = os.environ.get('TELEGRAM_API_ID')
API_HASH = os.environ.get('TELEGRAM_API_HASH')
SESSION_STR = os.environ.get('TELEGRAM_SESSION')

TELEGRAM_CHANNEL_TIMEOUT_SEC = 15.0
TELEGRAM_MAX_TEXT_CHARS = 1000  # Increased slightly for better data quality

async def main():
    if not API_ID or not API_HASH or not SESSION_STR:
        print("❌ Error: Missing Telegram credentials in .env")
        return

    # 1. Load Channel Configuration
    if not CONFIG_FILE.exists():
        print(f"❌ Error: Config file not found at {CONFIG_FILE}")
        return

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    # Flatten all enabled channels from all categories (full, tech, etc.)
    channels_to_crawl = []
    for category in config_data.get('channels', {}):
        for ch in config_data['channels'][category]:
            if ch.get('region') != 'iran':
                continue
            if ch.get('enabled'):
                channels_to_crawl.append(ch)

    print(f"📂 Loaded {len(channels_to_crawl)} enabled channels from config.")

    # 2. Initialize Telegram Client
    client = TelegramClient(StringSession(SESSION_STR), int(API_ID), API_HASH)
    
    all_extracted_posts = []

    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Session invalid or expired.")
            return

        print("✅ Telegram Connected.\n")

        for ch_config in channels_to_crawl:
            handle = ch_config['handle']
            max_msgs = ch_config.get('maxMessages', 10)
            
            print(f"📡 Crawling @{handle} (Limit: {max_msgs})...")
            
            try:
                # Get Entity
                entity = await asyncio.wait_for(
                    client.get_entity(handle),
                    timeout=TELEGRAM_CHANNEL_TIMEOUT_SEC
                )

                # Get Messages
                msgs = await asyncio.wait_for(
                    client.get_messages(entity, limit=max_msgs),
                    timeout=TELEGRAM_CHANNEL_TIMEOUT_SEC
                )

                channel_posts_count = 0
                for msg in msgs:
                    if not msg or not msg.text:
                        continue
                    
                    # Clean and truncate text
                    clean_text = msg.text.strip()
                    if len(clean_text) > TELEGRAM_MAX_TEXT_CHARS:
                        clean_text = clean_text[:TELEGRAM_MAX_TEXT_CHARS] + "..."

                    # Prepare data object
                    post_data = {
                        "channel_handle": handle,
                        "channel_label": ch_config.get('label'),
                        "post_id": msg.id,
                        "date": msg.date.isoformat() if msg.date else None,
                        "text": clean_text,
                        "topic": ch_config.get('topic'),
                        "region": ch_config.get('region'),
                        "tier": ch_config.get('tier'),
                        "url": f"https://t.me/{handle}/{msg.id}"
                    }
                    
                    all_extracted_posts.append(post_data)
                    channel_posts_count += 1

                print(f"   ✅ Extracted {channel_posts_count} posts.")
                
                # Anti-Flood Delay
                await asyncio.sleep(1.5)

            except asyncio.TimeoutError:
                print(f"   ⚠️ Timeout skipping @{handle}")
            except FloodWaitError as e:
                print(f"   🚨 FloodWait: Need to wait {e.seconds}s. Stopping crawl.")
                break
            except Exception as e:
                print(f"   ❌ Error crawling @{handle}: {e}")

        # 3. Save Results to JSON
        output_payload = {
            "updatedAt": datetime.utcnow().isoformat() + "Z",
            "total_posts": len(all_extracted_posts),
            "posts": all_extracted_posts
        }

        # Ensure directory exists
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_payload, f, ensure_ascii=False, indent=2)

        print(f"\n✨ Successfully saved {len(all_extracted_posts)} posts to {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ Global error: {e}")
    finally:
        await client.disconnect()
        print("🔌 Disconnected.")

if __name__ == '__main__':
    asyncio.run(main())