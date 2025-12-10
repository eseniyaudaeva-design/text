import requests
from bs4 import BeautifulSoup
import openai
import pandas as pd
import time
import os

# --- НАСТРОЙКИ ---
API_KEY = os.getenv("PERPLEXITY_API_KEY")
TARGET_URL = os.getenv("INPUT_URL")

if not API_KEY:
    raise ValueError("Ошибка: Не найден API ключ PERPLEXITY_API_KEY!")
if not TARGET_URL:
    raise ValueError("Ошибка: Не введена ссылка для обработки!")

BASE_URL_API = "https://api.perplexity.ai"
client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL_API)

# --- СТАТИЧЕСКИЙ КОНТЕНТ (ШАБЛОНЫ) ---
# Этот текст будет одинаковым во всех строках
STATIC_DATA = {
    'IP_PROP4817': "Условия поставки",
    'IP_PROP4818': "Оперативные отгрузки в регионы точно в срок",
    'IP_PROP4819': """<p>Надежная и быстрая доставка заказа в любую точку страны: "Стальметурал" отгружает товар 24 часа в сутки, 7 дней в неделю. Более 4 000 отгрузок в год. При оформлении заказа менеджер предложит вам оптимальный логистический маршрут.</p>""",
    
    'IP_PROP4820': """<p>Наши изделия успешно применяются на некоторых предприятиях Урала, центрального региона, Поволжья, Сибири. Партнеры по логистике предложат доставить заказ самым удобным способом – автомобильным, железнодорожным, даже авиационным транспортом. Для вас разработают транспортную схему под удобный способ получения. Погрузка выполняется полностью с соблюдением особенностей техники безопасности.</p>
<div class="h4">
<h4>Самовывоз</h4>
</div>
<p>Если обычно соглашаетесь самостоятельно забрать товар или даете это право уполномоченным, адрес и время работы склада в своем городе уточняйте у менеджера.</p>
<div class="h4">
<h4>Грузовой транспорт компании</h4>
</div>
<p>Отправим прокат на ваш объект собственным автопарком. Получение в упаковке для безопасной транспортировки, а именно на деревянном поддоне.</p>
<div class="h4">
<h4>Сотрудничаем с ТК</h4>
</div>
<p>Доставка с помощью транспортной компании по России и СНГ. Окончательная цена может измениться, так как ссылается на прайс-лист, который предоставляет контрагент, однако, сравним стоимость логистических служб и выберем лучшую.</p>""",

    'IP_PROP4821': "Оплата и реквизиты для постоянных клиентов:",
    'IP_PROP4822': """<p>Наша компания готова принять любые комфортные виды оплаты для юридических и физических лиц: по счету, наличная и безналичная, наложенный платеж, также возможны предоплата и отсрочка платежа.</p>""",
    
    'IP_PROP4823': """<div class="h4">
        <h3>Примеры возможной оплаты</h3>
</div>
<div class="an-col-12">
        <ul>
                <li style="font-weight: 400;">
                <p>
 <span style="font-weight: 400;">С помощью менеджера в центрах продаж</span>
                </p>
 </li>
        </ul>
        <p>
                 Важно! Цена не является публичной офертой. Приходите в наш офис, чтобы уточнить поступление, получить ответы на почти любой вопрос, согласовать возврат, счет, рассчитать логистику.
        </p>
        <ul>
                <li style="font-weight: 400;">
                <p>
 <span style="font-weight: 400;">На расчетный счет</span>
                </p>
 </li>
        </ul>
        <p>
                 По внутреннему счету в отделении банка или путем перечисления средств через личный кабинет (транзакции защищены, скорость зависит от отделения). Для права подтверждения нужно показать согласие на платежное поручение с отметкой банка.
        </p>
        <ul>
                <li style="font-weight: 400;">
                <p>
 <span style="font-weight: 400;">Наличными или банковской картой при получении</span>
                </p>
 </li>
        </ul>
        <p>
 <span style="font-weight: 400;">Поможем с оплатой: объем имеет значение. Крупным покупателям – деньги можно перевести после приемки товара.</span>
        </p>
        <p>
                 Менеджеры предоставят необходимую информацию.
        </p>
                <p>
                         Заказывайте через прайс-лист:
                </p>
                <p>
 <a class="btn btn-blue" href="/catalog/">Каталог (магазин-меню):</a>
                </p>
        </div>
</div>
 <br>""",

    'IP_PROP4824': "Описание, статьи, поиск, отзывы, новости, акции, журнал, info:",
    'IP_PROP4825': "Можем металлизировать, оцинковать, никелировать, проволочь",
    'IP_PROP4826': "Современный практический подход",
    
    'IP_PROP4834': "Надежность без примесей",
    'IP_PROP4835': "Популярный поставщик",
    'IP_PROP4836': "Качество и характер",
    'IP_PROP4837': "Порядок в ГОСТах"
}

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
    """

    try:
        response = client.chat.completions.create(
            model="sonar-pro", 
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content
        blocks = content.split("|||BLOCK_SEP|||")
        clean_blocks = [b.strip() for b in blocks if b.strip()]
        
        while len(clean_blocks) < 5:
            clean_blocks.append("")
            
        return clean_blocks[:5]

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
        
        # 1. Генерируем уникальные тексты
        blocks = generate_five_blocks(base_text_content, tag['name'])
        
        # 2. Собираем строку: Смешиваем уникальные данные и статические шаблоны
        row = {
            'TagName': tag['name'],
            'URL': tag['url'],
            
            # --- УНИКАЛЬНЫЕ ГЕНЕРИРУЕМЫЕ ТЕКСТЫ ---
            'IP_PROP4839': blocks[0], # Текст 1
            'IP_PROP4816': blocks[1], # Текст 2
            'IP_PROP4838': blocks[2], # Текст 3
            'IP_PROP4829': blocks[3], # Текст 4
            'IP_PROP4831': blocks[4], # Текст 5
            
            # --- СТАТИЧЕСКИЕ ДАННЫЕ (ИЗ ВАШЕГО CSV) ---
            'IP_PROP4817': STATIC_DATA['IP_PROP4817'],
            'IP_PROP4818': STATIC_DATA['IP_PROP4818'],
            'IP_PROP4819': STATIC_DATA['IP_PROP4819'],
            'IP_PROP4820': STATIC_DATA['IP_PROP4820'],
            'IP_PROP4821': STATIC_DATA['IP_PROP4821'],
            'IP_PROP4822': STATIC_DATA['IP_PROP4822'],
            'IP_PROP4823': STATIC_DATA['IP_PROP4823'],
            'IP_PROP4824': STATIC_DATA['IP_PROP4824'],
            'IP_PROP4825': STATIC_DATA['IP_PROP4825'],
            'IP_PROP4826': STATIC_DATA['IP_PROP4826'],
            'IP_PROP4834': STATIC_DATA['IP_PROP4834'],
            'IP_PROP4835': STATIC_DATA['IP_PROP4835'],
            'IP_PROP4836': STATIC_DATA['IP_PROP4836'],
            'IP_PROP4837': STATIC_DATA['IP_PROP4837'],
        }
        all_rows.append(row)
        time.sleep(1.5)

    # Порядок столбцов в итоговом файле
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
    df = df.reindex(columns=columns_order)
    
    filename = 'seo_texts_result.xlsx'
    df.to_excel(filename, index=False)
    print(f"Готово! Файл {filename} создан.")

else:
    print("Ошибка: Не удалось получить данные со страницы.")
    pd.DataFrame().to_excel('seo_texts_result.xlsx')
