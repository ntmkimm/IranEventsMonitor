import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import AuthKeyDuplicatedError, FloodWaitError

# Ép UTF-8 cho Terminal để in emoji không bị lỗi trên Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Load biến môi trường từ file .env
load_dotenv()

api_id_str = os.environ.get('TELEGRAM_API_ID', '')
api_hash = os.environ.get('TELEGRAM_API_HASH', '')
session_str = os.environ.get('TELEGRAM_SESSION', '')

if not api_id_str or not api_hash or not session_str:
    print("❌ Thiếu TELEGRAM_API_ID, TELEGRAM_API_HASH, hoặc TELEGRAM_SESSION trong file .env")
    sys.exit(1)

try:
    api_id = int(api_id_str)
except ValueError:
    print("❌ TELEGRAM_API_ID phải là một số.")
    sys.exit(1)

# Giới hạn 15s cho mỗi hành động theo đúng chuẩn kiến trúc của bạn
TELEGRAM_CHANNEL_TIMEOUT_SEC = 15.0
TELEGRAM_MAX_TEXT_CHARS = 800

async def main():
    print("⏳ Đang kết nối tới Telegram (MTProto)...")
    
    # Khởi tạo Client
    client = TelegramClient(
        StringSession(session_str), 
        api_id, 
        api_hash, 
        connection_retries=3
    )

    try:
        await client.connect()
        
        # Kiểm tra xem session có thực sự hợp lệ không
        if not await client.is_user_authorized():
            print("❌ Session không hợp lệ hoặc đã hết hạn.")
            return
            
        print("✅ Đã kết nối Telegram thành công!\n")

        # Chỉ test 2 kênh để đảm bảo an toàn cho tài khoản
        channels_to_test = ['VahidOnline', 'abualiexpress']

        for handle in channels_to_test:
            print(f"📡 Đang lấy dữ liệu từ kênh: @{handle}")
            
            try:
                # 1. Lấy thông tin Entity của kênh (có timeout 15s)
                # Sử dụng asyncio.wait_for thay cho hàm withTimeout tự viết
                entity = await asyncio.wait_for(
                    client.get_entity(handle),
                    timeout=TELEGRAM_CHANNEL_TIMEOUT_SEC
                )

                # 2. Lấy 3 tin nhắn mới nhất (có timeout 15s)
                msgs = await asyncio.wait_for(
                    client.get_messages(entity, limit=3),
                    timeout=TELEGRAM_CHANNEL_TIMEOUT_SEC
                )

                count = 0
                for msg in msgs:
                    if not msg or not msg.id:
                        continue
                    
                    # msg.text lấy text của tin nhắn (hoặc caption của ảnh/video)
                    text = msg.text
                    
                    # Bỏ qua nếu tin nhắn chỉ có Media (ảnh/video) mà không có Text
                    if not text:
                        print(f"   ⏭️  Bỏ qua tin nhắn ID: {msg.id} (Chỉ có Media, không text)")
                        continue

                    # Cắt ngắn chuỗi nếu quá dài
                    if len(text) > TELEGRAM_MAX_TEXT_CHARS:
                        text = text[:TELEGRAM_MAX_TEXT_CHARS] + '... [ĐÃ CẮT NGẮN]'
                    
                    # Format thời gian (chuyển datetime UTC sang timezone của máy)
                    if msg.date:
                        ts = msg.date.astimezone().strftime('%d/%m/%Y %H:%M:%S')
                    else:
                        ts = 'Unknown Time'

                    print(f"\n   🔹[{ts}] ID: {msg.id}")
                    print(f"   📝 Nội dung: {text.replace(chr(10), ' ↵ ')}")
                    count += 1
                
                print(f"\n✅ Lấy thành công {count} tin nhắn từ @{handle}\n-----------------------------------")
                
                # Nghỉ 1 giây trước khi qua kênh tiếp theo để chống Flood
                await asyncio.sleep(1)

            # --- Xử lý lỗi chuẩn của Python / Telethon ---
            except asyncio.TimeoutError:
                print(f"❌ Lỗi timeout khi lấy dữ liệu kênh {handle} sau {TELEGRAM_CHANNEL_TIMEOUT_SEC}s")
                
            except AuthKeyDuplicatedError:
                print("🚨 Session bị vô hiệu hóa (AUTH_KEY_DUPLICATED) — Bạn đang đăng nhập ở 2 nơi cùng lúc!")
                break
                
            except FloodWaitError as e:
                # Telethon tự động bóc tách số giây đợi vào e.seconds
                print(f"🚨 Bị Telegram giới hạn (FLOOD_WAIT) {e.seconds} giây — Ngừng chu kỳ sớm!")
                break
                
            except Exception as e:
                print(f"❌ Lỗi khi lấy dữ liệu kênh {handle}: {e}")

    except Exception as err:
        print(f"❌ Lỗi kết nối khởi tạo: {err}")
    finally:
        print("🔌 Đang ngắt kết nối an toàn...")
        if client.is_connected():
            await client.disconnect()

if __name__ == '__main__':
    # Chạy event loop của asyncio
    asyncio.run(main())