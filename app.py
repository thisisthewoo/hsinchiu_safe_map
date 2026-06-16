# -*- coding: utf-8 -*-

import re
import pandas as pd
import folium
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import math

st.set_page_config(page_title="新竹安心出遊地圖", layout="wide")

# ── 讀取資料 ──────────────────────────────────────────────
@st.cache_data
def load_data():
    # 美食資料
    food = pd.read_csv("新竹美食_final.csv")
    food = food[food["geocode_status"] == "found"].copy()
    food["lat"] = pd.to_numeric(food["lat"], errors="coerce")
    food["lon"] = pd.to_numeric(food["lon"], errors="coerce")
    food["like_count"] = pd.to_numeric(food["like_count"], errors="coerce").fillna(0)
    food["taken_at"] = pd.to_datetime(food["taken_at"], errors="coerce")
    food["year"] = food["taken_at"].dt.year.fillna(0).astype(int)

    # 補縮圖
    thumb_rows = []
    with open("新竹美食.ndjson", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            d = r["data"]
            image_versions = d.get("image_versions2", {}) or {}
            candidates = image_versions.get("candidates", []) or []
            thumbnail = candidates[-1]["url"] if candidates else ""
            thumb_rows.append({
                "post_code": d.get("code", ""),
                "thumbnail": thumbnail
            })

    df_thumb = pd.DataFrame(thumb_rows)
    food = food.merge(df_thumb, on="post_code", how="left")

    # 店名
    def extract_store_name(caption, address):
        if not caption or not address:
            return ""

        lines = caption.replace("\\n", "\n").split("\n")

        for i, line in enumerate(lines):
            if address.replace(", ", "") in line.replace(", ", ""):
                for j in range(i - 1, max(i - 4, -1), -1):
                    prev = lines[j].strip()
                    prev = re.sub(r'^[\d\.\s🏷️📍🏠✅⚠️💡◼️►\-\*]+', '', prev).strip()
                    prev = re.sub(r'^(店家|地址|名稱)\s*[:：]\s*', '', prev).strip()
                    if prev and len(prev) > 1:
                        return prev

        return ""

    def clean_store_name(name):
        if not name:
            return ""

        if re.search(r'\d{4}\s?\d{3}\s?\d{3}', name):
            return ""

        name = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩\d\.\s🌟⭐✨🔆💫]+', '', name).strip()
        name = re.sub(r'\s*@\w+.*$', '', name).strip()

        if len(name) > 15:
            return ""

        return name

    food["store_name"] = food.apply(
        lambda row: extract_store_name(row["caption"], row["address"]),
        axis=1
    )
    food["store_name"] = food["store_name"].apply(clean_store_name)
    food["display_name"] = food.apply(
        lambda row: row["store_name"] if row["store_name"] else row["address"],
        axis=1
    )

    # 美食行政區
    def get_area(address):
        areas = [
            "東區", "北區", "香山區",
            "竹北市", "竹東鎮", "湖口鄉",
            "新埔鎮", "關西鎮", "新豐鄉", "芎林鄉"
        ]
        for a in areas:
            if a in str(address):
                return a
        return "其他"

    # 食物分類
    def get_food_type(row):
        name = str(row.get("display_name", "")) + str(row.get("caption", ""))

        if re.search(r'拉麵|河粉|米粉|麵食|麵館|抄手|餛飩|粄條|螺螄粉', name):
            return "麵食"
        if re.search(r'火鍋|涮涮鍋|鍋物', name):
            return "火鍋"
        if re.search(r'牛排|豬排|排骨|雞排|燒肉|烤肉', name):
            return "燒烤肉類"
        if re.search(r'壽司|生魚片|日式|丼|天婦羅', name):
            return "日式料理"
        if re.search(r'披薩|義大利|pasta|漢堡|三明治', name, re.IGNORECASE):
            return "西式料理"
        if re.search(r'咖啡|cafe|coffee|下午茶|甜點|蛋糕|鬆餅|可頌', name, re.IGNORECASE):
            return "咖啡甜點"
        if re.search(r'珍奶|手搖|飲料|茶飲|果汁', name):
            return "手搖飲料"
        if re.search(r'早餐|早午餐|brunch', name, re.IGNORECASE):
            return "早午餐"
        if re.search(r'小籠包|水餃|煎餃|包子|饅頭', name):
            return "點心麵食"
        if re.search(r'海鮮|蝦|生蠔|蛤蜊|魚', name):
            return "海鮮"
        if re.search(r'冰|剉冰|雪花冰|芋圓|豆花', name):
            return "冰品"
        if re.search(r'臭豆腐|肉圓|鹽酥雞|炸物|滷味', name):
            return "台式小吃"

        return "其他"

    def get_friendly_type(row):
        text = (
            str(row.get("display_name", "")) +
            str(row.get("caption", "")) +
            str(row.get("address", ""))
        )

        # 親子友善：需要「親子/兒童/小孩/孩子」
        family_target_keywords = r"親子|兒童|小孩|孩子|小朋友|寶寶|嬰兒|親子友善|兒童友善"

        # 寵物友善：需要「寵物/毛孩/狗/貓」
        pet_target_keywords = r"寵物|毛孩|毛小孩|狗狗|貓咪|狗|貓|寵物友善|寵物餐廳|汪星人|喵星人"

        family = (
            re.search(family_target_keywords, text)
        )

        pet = (
            re.search(pet_target_keywords, text)
        )

        if family:
            return "親子友善"

        if pet:
            return "寵物友善"

        return "一般"

    food["area"] = food["address"].apply(get_area)
    food["food_type"] = food.apply(get_food_type, axis=1)
    food["friendly_type"] = food.apply(get_friendly_type, axis=1)

    food["post_url"] = food["post_code"].apply(
        lambda x: f"https://www.instagram.com/p/{x}/" if pd.notna(x) else ""
    )

       # 性犯罪熱點資料
    crime = pd.read_csv("婦幼安全警示_新竹.csv")
    crime["lat"] = pd.to_numeric(crime["lat"], errors="coerce")
    crime["lon"] = pd.to_numeric(crime["lon"], errors="coerce")
    crime = crime.dropna(subset=["lat", "lon"]).copy()

    # 第一階段：先從 name 文字判斷行政區
    def get_crime_area_by_name(name):
        name = str(name)

        for area in [
            "東區", "北區", "香山區",
            "竹北市", "竹東鎮", "湖口鄉",
            "新埔鎮", "關西鎮", "新豐鄉", "芎林鄉"
        ]:
            if area in name:
                return area

        return ""

    # 第二階段：若 name 無法判斷行政區，標記為「未分類」
    # 之後使用者只要有選任一性犯罪熱點地區，未分類資料也會一起顯示
    crime["area"] = crime["name"].apply(get_crime_area_by_name)
    crime["area"] = crime["area"].replace("", "未分類")

    return food, crime
food_found, df_crime = load_data()

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # 公尺
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ── 側邊篩選器 ────────────────────────────────────────────
st.sidebar.subheader("📍 地址／路名查詢")

user_address = st.sidebar.text_input(
    "輸入地址或路名",
    placeholder="例如：光復路、東門街、新竹市東區學府路",
    key="address_search_input"
)

st.sidebar.title("🔍 篩選器")

all_areas = [
    "東區", "北區", "香山區",
    "竹北市", "竹東鎮", "湖口鄉",
    "新埔鎮", "關西鎮", "新豐鄉", "芎林鄉",
    "其他"
]

crime_areas = ["東區", "北區", "香山區",
            "竹北市", "竹東鎮", "湖口鄉",
            "新埔鎮", "關西鎮", "新豐鄉", "芎林鄉"]
st.sidebar.subheader("📍 依地區與類型查詢")


all_foods = [
    "咖啡甜點", "燒烤肉類", "麵食", "其他", "火鍋", "日式料理",
    "海鮮", "西式料理", "台式小吃", "早午餐", "冰品", "手搖飲料", "點心麵食"
]

st.sidebar.subheader("🍜 美食")

selected_food_areas = st.sidebar.multiselect(
    "美食地區",
    options=all_areas,
    default=[]
)

selected_foods = st.sidebar.multiselect(
    "食物類型",
    options=all_foods,
    default=[]
)

all_friendly_types = [
    "親子友善",
    "寵物友善",
    "一般"
]

selected_friendly_types = st.sidebar.multiselect(
    "友善分類",
    options=all_friendly_types,
    default=[]
)

min_likes = st.sidebar.slider(
    "最低按讚數",
    0,
    10000,
    100,
    step=100
)

st.sidebar.subheader("⚠️ 性犯罪熱點")

selected_crime_areas = st.sidebar.multiselect(
    "熱點地區",
    options=crime_areas,
    default=[]
)

# ── 美食資料篩選：若有輸入路名，先依路名縮小，再套用下方篩選器 ──
food_to_show = food_found.iloc[0:0].copy()

has_address_query = bool(user_address and user_address.strip())
has_food_filter = bool(selected_food_areas or selected_foods or selected_friendly_types)

if has_address_query or has_food_filter:
    food_to_show = food_found[food_found["like_count"] >= min_likes].copy()

    # 先套用地址／路名
    if has_address_query:
        keyword = user_address.strip()
        food_to_show = food_to_show[
            food_to_show["address"].astype(str).str.contains(keyword, na=False, regex=False)
        ]

    # 再套用美食地區
    if selected_food_areas:
        food_to_show = food_to_show[
            food_to_show["area"].isin(selected_food_areas)
        ]

    # 再套用食物類型
    if selected_foods:
        food_to_show = food_to_show[
            food_to_show["food_type"].isin(selected_foods)
        ]

    # 再套用友善分類
    if selected_friendly_types:
        food_to_show = food_to_show[
            food_to_show["friendly_type"].isin(selected_friendly_types)
        ]

# ── 性犯罪熱點篩選：若有輸入路名，先依路名縮小，再套用地區篩選 ──
crime_to_show = df_crime.iloc[0:0].copy()

has_crime_filter = bool(selected_crime_areas)

if has_address_query or has_crime_filter:
    crime_to_show = df_crime.copy()

    # 先套用地址／路名
    if has_address_query:
        keyword = user_address.strip()
        crime_to_show = crime_to_show[
            crime_to_show["name"].astype(str).str.contains(keyword, na=False, regex=False)
        ]

    # 再套用熱點地區
    if selected_crime_areas:
        crime_to_show = crime_to_show[
            crime_to_show["area"].isin(selected_crime_areas) |
            (crime_to_show["area"] == "未分類")
        ]

# ── 標題 ──────────────────────────────────────────────────
st.title("🗺️ 新竹安心出遊地圖")

if food_to_show.empty and crime_to_show.empty:
    st.info("請先在左側篩選器選擇美食地區／食物類型，或選擇性犯罪熱點地區。")
else:
    st.markdown(
        f"目前顯示 **{len(food_to_show)}** 筆美食景點　｜　"
f"性犯罪熱點 **{len(crime_to_show)}** 筆"
    )

# ── 地圖 ──────────────────────────────────────────────────
m = folium.Map(
    location=[24.80, 120.97],
    zoom_start=13,
    tiles="Cartodb Positron"
)

# 美食圖層
food_group = folium.FeatureGroup(name="🍜 美食景點")

for _, row in food_to_show.iterrows():
    popup_text = f"""
        <img src="{row.get('thumbnail', '')}" width="200"><br>
        <b>{row['display_name']}</b><br>
        📍 {row['address']}<br>
        🏙️ {row['area']}<br>
        🍽️ {row['food_type']}<br>
        🧩 {row['friendly_type']}<br>
        ❤️ {int(row['like_count'])} likes<br>
        📅 {row['taken_at']}<br>
        <a href="{row['post_url']}" target="_blank">📸 看原始貼文</a>
    """

    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=folium.Popup(popup_text, max_width=250),
        tooltip=row["display_name"],
        icon=folium.Icon(color="blue", icon="cutlery", prefix="fa")
    ).add_to(food_group)

# 性犯罪熱點圖層
crime_group = folium.FeatureGroup(name="⚠️ 性犯罪熱點")

if not crime_to_show.empty:
    HeatMap(
        crime_to_show[["lat", "lon"]].values.tolist(),
        radius=40,
        blur=25,
        min_opacity=0.25,
        gradient={"0.4": "yellow", "0.7": "orange", "1.0": "red"}
    ).add_to(crime_group)

for _, row in crime_to_show.iterrows():
    popup_text = f"""
        🚨 性犯罪熱點<br>
        📍 {row['name']}<br>
        🏙️ 行政區：{row['area']}
    """

    folium.Marker(
        location=[float(row["lat"]), float(row["lon"])],
        popup=folium.Popup(popup_text, max_width=220),
        tooltip=f"🚨 性犯罪熱點｜{row['name']}",
        icon=folium.Icon(color="red", icon="exclamation-sign", prefix="glyphicon")
    ).add_to(crime_group)

food_group.add_to(m)
crime_group.add_to(m)
folium.LayerControl().add_to(m)

st_folium(
    m,
    width=1200,
    height=600,
    key="hsinchu_safe_map",
    returned_objects=[],
)