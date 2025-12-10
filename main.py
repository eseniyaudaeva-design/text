import requests
from bs4 import BeautifulSoup
import openai
import pandas as pd
import time
import os
import sys

# --- НАСТРОЙКИ (Берем из переменных окружения GitHub) ---
API_KEY = os.getenv("PERPLEXITY_API_KEY")
TARGET_URL = os.getenv("INPUT_URL")

if not API_KEY:
    raise ValueError("Ошибка: Не найден API ключ PERPLEXITY_API_KEY в секретах!")
if not TARGET_URL:
    raise ValueError("Ошибка: Не введена ссылка для обработки!")

BASE_URL_API = "https://api.perplexity.ai"

# Инициализация клиента
client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL_API)

def get_page_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
    except Exception as e:
        print(f"Connection Error: {e}")
        return None, None
    
    if response.status_code != 200:
        print(f"Status Code Error: {response.status_code}")
        return None, None

    soup = BeautifulSoup(response.text, 'html.parser')

    description_div = soup.find('div', class_='description-container')
    base_text = description_div.get_text(separator="\n", strip=True) if description_div else ""

    tags_container = soup.find(class_='popular-tags-inner')
    tags_data = []
    
    if tags_container:
        links = tags_container.find_all('a')
        for link in links:
            tag_name = link.get_text(strip=True)
            tag_url = link.get('href')
            if tag_url and tag_url.startswith('/'):
                # Пытаемся собрать полную ссылку, если она относительная
                from urllib.parse import urljoin
                tag_url = urljoin(url, tag_url)
            tags_data.append({'name': tag_name, 'url': tag_url})
    
    return base_text, tags_data

def generate_unique_text(base_text, tag_name):
    if not base_text: return "Error: No donor text."
    
    system_instruction = "Ты — ведущий технический редактор. Твоя задача — генерировать уникальные SEO тексты."
    
    user_prompt = f"""
    ВВОДНЫЕ ДАННЫЕ:
    1. Товар: "{tag_name}".
    2. Базовый текст: \"\"\"{base_text[:3000]}\"\"\"

    ЗАДАЧА: Напиши коммерческий SEO-текст для страницы "{tag_name}".
    Структура HTML: h2, 2 абзаца, ul список.
    Язык: Русский. Без markdown, только чистый HTML.
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-sonar-large-128k-online",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)[:100]}"

# --- ЗАПУСК ---
print(f"Обрабатываем страницу: {TARGET_URL}")
base_text_content, tags = get_page_data(TARGET_URL)

if tags and base_text_content:
    total_tags = len(tags)
    print(f"Найдено тегов: {total_tags}")
    
    results = []
    # Для теста можно ограничить количество, например tags[:3], чтобы не тратить лимиты
    for i, tag in enumerate(tags, 1): 
        print(f"[{i}/{total_tags}] Генерируем для: {tag['name']}...")
        new_text = generate_unique_text(base_text_content, tag['name'])
        results.append({'TagName': tag['name'], 'URL': tag['url'], 'GeneratedText': new_text})
        time.sleep(1)

    df = pd.DataFrame(results)
    filename = 'seo_texts_result.xlsx'
    df.to_excel(filename, index=False)
    print(f"Файл {filename} создан.")
else:
    print("Ошибка: Теги или текст не найдены.")
    # Создаем пустой файл, чтобы Action не падал при загрузке артефакта
    pd.DataFrame().to_excel('seo_texts_result.xlsx')