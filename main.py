import requests
from bs4 import BeautifulSoup
import openai
import pandas as pd
import time
import os
import re

# --- НАСТРОЙКИ ---
API_KEY = os.getenv("PERPLEXITY_API_KEY")
TARGET_URL = os.getenv("INPUT_URL")

if not API_KEY:
    raise ValueError("Ошибка: Не найден API ключ PERPLEXITY_API_KEY!")
if not TARGET_URL:
    raise ValueError("Ошибка: Не введена ссылка для обработки!")

BASE_URL_API = "https://api.perplexity.ai"
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
                from urllib.parse import urljoin
                tag_url = urljoin(url, tag_url)
            tags_data.append({'name': tag_name, 'url': tag_url})
    
    return base_text, tags_data

def generate_five_blocks(base_text, tag_name):
    if not base_text: return ["Error"] * 5

    system_instruction = """
    Ты — профессиональный технический копирайтер и SEO-специалист завода металлоконструкций.
    Твоя задача — написать 5 независимых текстовых блоков для карточки товара, строго следуя жесткой структуре.
    Никакого Markdown (болд, италик через звездочки запрещен). Только чистый HTML.
    """

    user_prompt = f"""
    ВВОДНЫЕ:
    Товар: "{tag_name}".
    База знаний (факты): \"\"\"{base_text[:3500]}\"\"\"

    ЗАДАЧА:
    Сгенерируй ровно 5 текстовых блоков. Темы блоков распредели логически (например: 1. Общее описание, 2. Характеристики, 3. Применение, 4. Услуги/Сервис, 5. Производство/Качество).

    СТРУКТУРА КАЖДОГО БЛОКА (СТРОГО):
    1. Заголовок:
       - Для Блока №1: тег <h2>Короткое название</h2>
       - Для Блоков №2-5: тег <h3>Короткое название</h3>
       - Названия информативные (напр: "Технические параметры", "Сфера применения", "Особенности производства").
    2. Первый абзац: <p>Текст...</p>
    3. Вводная фраза перед списком: <p>Фраза заканчивается на двоеточие:</p>
    4. Список (<ul> или <ol>):
       - Если перечисление свойств/преимуществ -> маркированный список <ul>.
       - Если этапы (производства, работ) -> нумерованный список <ol>.
       - Каждая строка <li>Начинается с Большой буквы... заканчивается точкой с запятой;</li>
       - Последняя строка списка <li>Заканчивается точкой.</li>
       - Внутри элементов списка ЗАПРЕЩЕНО использовать двоеточие ":", используй тире "–".
    5. Заключительный абзац: <p>Итоговый текст блока.</p>

    ТРЕБОВАНИЕ К ВЫВОДУ:
    Раздели эти 5 блоков специальным разделителем: |||BLOCK_SEP|||
    Не пиши никаких вступлений типа "Вот ваши тексты". Сразу код.
    
    Пример формата вывода:
    <h2>Заголовок 1</h2><p>...</p><p>...:</p><ul><li>...;</li><li>....</li></ul><p>...</p>
    |||BLOCK_SEP|||
    <h3>Заголовок 2</h3><p>...</p>...
    |||BLOCK_SEP|||
    ...и так далее 5 раз.
    """

    try:
        response = client.chat.completions.create(
            model="sonar-pro", # Используем актуальную модель
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content
        
        # Разбиваем ответ на блоки по разделителю
        blocks = content.split("|||BLOCK_SEP|||")
        
        # Чистим блоки от лишних пробелов и переносов
        clean_blocks = [b.strip() for b in blocks if b.strip()]
        
        # Если блоков меньше 5, дополняем пустыми
        while len(clean_blocks) < 5:
            clean_blocks.append("")
            
        return clean_blocks[:5] # Возвращаем ровно 5

    except Exception as e:
        return [f"Error: {str(e)[:50]}"] * 5

# --- ЗАПУСК ---
print(f"Запуск обработки для: {TARGET_URL}")
base_text_content, tags = get_page_data(TARGET_URL)

if tags and base_text_content:
    print(f"Найдено тегов: {len(tags)}. Генерируем контент...")
    
    all_rows = []
    
    for i, tag in enumerate(tags, 1):
        print(f"[{i}/{len(tags)}] {tag['name']}...")
        
        # Генерируем 5 блоков
        blocks = generate_five_blocks(base_text_content, tag['name'])
        
        # Формируем строку для Excel с точными ID столбцов
        row = {
            'TagName': tag['name'],
            'URL': tag['url'],
            
            # ТЕКСТОВЫЕ БЛОКИ (Сгенерированные)
            'IP_PROP4839': blocks[0], # Текст 1
            'IP_PROP4816': blocks[1], # Текст 2
            'IP_PROP4838': blocks[2], # Текст 3 (доп категории)
            'IP_PROP4829': blocks[3], # Текст 4 (услуги)
            'IP_PROP4831': blocks[4], # Текст 5 (производство)
            
            # СЛУЖЕБНЫЕ СТОЛБЦЫ (Пустые, для структуры)
            'IP_PROP4817': "", # Заголовок шагов покупки
            'IP_PROP4818': "", # Заголовок доставки
            'IP_PROP4819': "", # Абзац доставки 1
            'IP_PROP4820': "", # Абзац доставки 2
            'IP_PROP4821': "", # Заголовок оплаты
            'IP_PROP4822': "", # Абзац оплаты 1
            'IP_PROP4823': "", # Абзац оплаты 2
            'IP_PROP4824': "", # Заголовок прайс-лист
            'IP_PROP4825': "", # Надзаголовок преимуществ
            'IP_PROP4826': "", # Заголовок преимуществ
            'IP_PROP4834': "", # Сервис - Преимущества 1
            'IP_PROP4835': "", # Доставка - Преимущества 2
            'IP_PROP4836': "", # Оплата - Преимущества 3
            'IP_PROP4837': "", # Гарантия - Преимущества 4
        }
        all_rows.append(row)
        time.sleep(1.5) # Пауза для API

    # Сохраняем в Excel
    # Важно: задаем порядок столбцов, чтобы в файле было красиво
    columns_order = [
        'TagName', 'URL', 
        'IP_PROP4839', # Текст 1
        'IP_PROP4817', 'IP_PROP4818', 'IP_PROP4819', 'IP_PROP4820', 
        'IP_PROP4821', 'IP_PROP4822', 'IP_PROP4823', 'IP_PROP4824',
        'IP_PROP4816', # Текст 2
        'IP_PROP4825', 'IP_PROP4826', 
        'IP_PROP4834', 'IP_PROP4835', 'IP_PROP4836', 'IP_PROP4837',
        'IP_PROP4838', # Текст 3
        'IP_PROP4829', # Текст 4
        'IP_PROP4831'  # Текст 5
    ]
    
    df = pd.DataFrame(all_rows)
    # Переупорядочиваем столбцы (если каких-то нет в данных, pandas их создаст пустыми, но лучше так)
    df = df.reindex(columns=columns_order)
    
    filename = 'seo_texts_result.xlsx'
    df.to_excel(filename, index=False)
    print(f"Готово! Файл {filename} создан.")

else:
    print("Ошибка: Не удалось получить данные со страницы.")
    # Создаем пустой файл заглушку
    pd.DataFrame().to_excel('seo_texts_result.xlsx')
