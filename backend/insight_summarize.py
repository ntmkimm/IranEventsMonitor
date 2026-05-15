import os
import json
import glob
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load môi trường
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

LLM_API_URL = os.getenv("LLM_API_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "intelligence_insight.json")

def smart_truncate(data, limit=100):
    if isinstance(data, list):
        return data[:limit]
    if isinstance(data, dict):
        return {k: data[k] for k in list(data.keys())[:limit]}
    return data

def load_all_json_data():
    context = {}
    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    for file_path in json_files:
        file_name = os.path.basename(file_path)
        # Bỏ qua chính file insight để tránh loop dữ liệu cũ
        if file_name == "intelligence_insight.json" or file_name == "telegram_channels.json":
            continue
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                key = file_name.replace(".json", "").replace("-", "_")
                context[key] = smart_truncate(content)
        except Exception as e:
            print(f"Error reading {file_name}: {e}")
    return context

def generate_and_save_insight():
    print("🤖 Generating Intelligence Insight via LLM...")
    data_content = load_all_json_data()
    
    prompt_content = f"""
    Analyze the following geopolitical and economic data. 
    DATA SOURCES (JSON):
    {json.dumps(data_content, indent=2, ensure_ascii=False)}

    Please provide a structured intelligence report in English covering:
    - Oil prices and trends.
    - Aviation status (OpenSky).
    - Critical: News & Conflict (GDELT, Liveuamap, Telegram).
        Key Themes, Significant Events, Conflict Zones, Diplomatic Efforts, Local Protests, Military Activities.
    - Critical: Security & Travel risks.
        Do Not Travel, Reconsider Travel, Caution.
    - Critical: Strategic outlook.
    - Conclusion.
    Format the output in professional Markdown.
    """

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a professional intelligence analyst. Output strictly in Markdown."},
            {"role": "user", "content": prompt_content}
        ],
        "temperature": 0.5
    }

    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}

    try:
        response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Lưu vào file JSON
            output_data = {
                "content": content,
                "updated_at": datetime.now().isoformat(),
                "model": LLM_MODEL
            }
            
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Insight saved to {OUTPUT_FILE}")
            return output_data
        else:
            print(f"❌ API Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ System Error: {str(e)}")
        return None

if __name__ == "__main__":
    generate_and_save_insight()