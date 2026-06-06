import re
import pandas as pd
import folium
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium
 
st.set_page_config(page_title="新竹安心出遊地圖", layout="wide")
 
# 讀取資料 
@st.cache_data
def load_data():
    food = pd.read_csv("新竹美食_final.csv")
    safety = pd.read_csv("婦幼安全警示_新竹.csv")
 
    food["lat"] = pd.to_numeric(food["lat"], errors="coerce")
    food["lon"] = pd.to_numeric(food["lon"], errors="coerce")
    food["like_count"] = pd.to_numeric(food["like_count"], errors="coerce").fillna(0)
    food["taken_at"] = pd.to_datetime(food["taken_at"], errors="coerce")
    food["year"] = food["taken_at"].dt.year.fillna(0).astype(int)
 
    safety["lat"] = pd.to_numeric(safety["lat"], errors="coerce")
    safety["lon"] = pd.to_numeric(safety["lon"], errors="coerce")
    safety = safety.dropna(subset=["lat", "lon"])
 
    # 年份標籤
    def simplify_year(year):
        if year <= 2021:
            return "2021以前"
        return str(year)
    food["year_label"] = food["year"].apply(simplify_year)
 
    # 食物分類
    def get_food_type(row):
        cap = str(row.get("caption", ""))
        tags = " ".join(re.findall(r'#(\w+)', cap))
        name = str(row.get("display_name", "")) + cap
 
        if re.search(r'咖啡廳|咖啡|下午茶', tags): return "咖啡廳"
        if re.search(r'甜點|蛋糕|冰淇淋', tags): return "甜點冰品"
        if re.search(r'火鍋', tags): return "火鍋"
        if re.search(r'早午餐', tags): return "早午餐"
        if re.search(r'早餐', tags): return "早餐"
        if re.search(r'燒肉|烤肉', tags): return "燒烤肉類"
        if re.search(r'拉麵|米粉|麵食', tags): return "麵食"
        if re.search(r'日式', tags): return "日式料理"
        if re.search(r'韓式|韓國', tags): return "韓式料理"
        if re.search(r'義大利麵|西式', tags): return "西式料理"
        if re.search(r'海鮮', tags): return "海鮮"
        if re.search(r'冰品|剉冰', tags): return "甜點冰品"
        if re.search(r'手搖|珍奶', tags): return "手搖飲料"
        if re.search(r'水餃|小籠包', tags): return "點心麵食"
        if re.search(r'麵線|拌麵|拉麵|河粉|米粉|麵食|麵館|抄手|餛飩|粄條|螺螄粉|意麵|酸辣粉|陽春麵|乾麵|泡麵', name): return "麵食"
        if re.search(r'火鍋|涮涮鍋|鍋物|薑母鴨|麻辣鍋', name): return "火鍋"
        if re.search(r'牛排|豬排|排骨|雞排|燒肉|烤肉|串燒|烤鴨', name): return "燒烤肉類"
        if re.search(r'壽司|生魚片|日式|丼|天婦羅|居酒屋|關東煮|日本料理|日料', name): return "日式料理"
        if re.search(r'韓式|韓國|泡菜|部隊鍋|韓國烤肉', name): return "韓式料理"
        if re.search(r'披薩|義大利|pasta|漢堡|三明治', name, re.IGNORECASE): return "西式料理"
        if re.search(r'咖啡|cafe|coffee|下午茶', name, re.IGNORECASE): return "咖啡廳"
        if re.search(r'甜點|蛋糕|鬆餅|可頌|冰淇淋|布丁|馬卡龍|麵包|吐司|貝果|可麗露|費南雪|巧克力', name): return "甜點冰品"
        if re.search(r'珍奶|手搖|飲料|茶飲|果汁', name): return "手搖飲料"
        if re.search(r'早午餐|brunch', name, re.IGNORECASE): return "早午餐"
        if re.search(r'早餐', name): return "早餐"
        if re.search(r'小籠包|水餃|煎餃|包子|饅頭|湯包', name): return "點心麵食"
        if re.search(r'海鮮|蝦|生蠔|蛤蜊|螃蟹|龍蝦|干貝|鮮蚵|牡蠣', name): return "海鮮"
        if re.search(r'冰|剉冰|雪花冰|芋圓|豆花', name): return "甜點冰品"
        if re.search(r'香腸|米腸|鐵板燒|炒飯|滷肉飯|控肉|魯肉|肉圓|臭豆腐|鹽酥雞|炸物|滷味|餡餅|喜餅|客家|大腸包小腸|蚵仔煎|古早味|麥芽糖|熱炒|鴨肉飯|潤餅|切仔麵|羊肉|牛雜|雞肉飯|米糕|魷魚羹|筒仔|粉肝|飯包|飯糰|雞飯', name): return "台式小吃"
        if re.search(r'泰式|越南|河粉|打拋|泰國|南洋|滇緬|海南雞|薑黃', name): return "東南亞料理"
        if re.search(r'素食|蔬食|全素|蛋奶素', name): return "素食"
        if re.search(r'港式|添好運|香港|飲茶', name): return "港式料理"
        return "其他"
 
    food["food_type"] = food.apply(get_food_type, axis=1)
 
    # 類別分類
    def get_category(row):
        is_family = bool(re.search(r'親子|兒童|小朋友|baby|kids|親子友善', str(row["caption"]), re.IGNORECASE))
        is_pet = bool(re.search(r'寵物|毛孩|狗友善|寵物友善|帶狗', str(row["caption"]), re.IGNORECASE))
        if is_family: return "親子友善"
        elif is_pet: return "寵物友善"
        else: return "一般美食"
 
    food["category"] = food.apply(get_category, axis=1)
 
    # 地區分類
    north_district = ['舊港里','港北里','海濱里','康樂里','南寮里','中寮里','福林里','古賢里','武陵里','士林里','境福里','光田里','湳中里','金華里','金雅里','湳雅里','光華里','舊社里','金竹里','長和里','水田里','新民里','北門里','新雅里','民富里','大同里','文雅里','中興里','中山里','磐石里','西門里','石坊里','潛園里','崇禮里','中央里','興南里','仁德里','西雅里','大鵬里','南勢里','台溪里','曲溪里','客雅里','中雅里','育英里','北區']
    east_district = ['東門里','中正里','親仁里','榮光里','育賢里','成功里','三民里','復中里','文華里','錦華里','復興里','前溪里','千甲里','水源里','東勢里','光復里','綠水里','東園里','公園里','東山里','建華里','光明里','武功里','豐功里','軍功里','建功里','立功里','埔頂里','龍山里','科園里','新莊里','關東里','仙水里','金山里','仙宮里','關新里','南門里','關帝里','南市里','福德里','振興里','新興里','頂竹里','下竹里','竹蓮里','寺前里','南大里','光鎮里','柴橋里','高峰里','新光里','湖濱里','明湖里','東區']
    hsiang_district = ['頂埔里','頂福里','中埔里','埔前里','牛埔里','虎林里','虎山里','港南里','香山里','大庄里','香村里','東香里','美山里','朝山里','樹下里','浸水里','海山里','鹽水里','內湖里','南港里','中隘里','南隘里','大湖里','茄苳里','香山區']
    zhubei = ['竹仁里','隘口里','中正村','勝利村','竹北里','竹義里','巨埔里','泰和里','鹿鳴里','竹北市']
    zhudong = ['竹東里','照門里','榮華里','公義里','信義村','中興村','自強里','山下里','三坑里','瑞峰里','溪州里','文山里','東勢里']
    hukuo = ['湖南村','湖鏡村','松柏村','山崎村','四座里']
    neiwang = ['內灣村','南興村','聯興里']
    xinpu = ['田新里','新埔里']
    guanxi = ['鳳凰村']
    baoshan = ['寶山村']
    beipu = ['北埔村']
    emei = ['峨眉村']
 
    def get_area_from_district(row):
        district = str(row.get("district", ""))
        address = str(row.get("address", ""))
        if district in east_district: return "東區"
        if district in north_district: return "北區"
        if district in hsiang_district: return "香山區"
        if district in zhubei: return "竹北市"
        if district in zhudong: return "竹東鎮"
        if district in hukuo: return "湖口鄉"
        if district in neiwang: return "橫山鄉"
        if district in xinpu: return "新埔鎮"
        if district in guanxi: return "關西鎮"
        if district in baoshan: return "寶山鄉"
        if district in beipu: return "北埔鄉"
        if district in emei: return "峨眉鄉"
        for area in ["竹北市","竹東鎮","湖口鄉","新埔鎮","關西鎮","新豐鄉","芎林鄉","橫山鄉","北埔鄉","寶山鄉","峨眉鄉"]:
            if area in address or area in district: return area
        return "其他"
 
    def fix_area(row):
        if row["area"] != "其他": return row["area"]
        address = str(row.get("address_clean", ""))
        if "東區" in address: return "東區"
        if "北區" in address: return "北區"
        if "香山區" in address: return "香山區"
        return "其他"
 
    food["area"] = food.apply(get_area_from_district, axis=1)
    food["area"] = food.apply(fix_area, axis=1)
    food = food[food["area"] != "其他"].copy()
    food = food[food["like_count"] >= 100].copy()
 
    return food, safety
 
food, safety = load_data()
 
#  側邊篩選器 
st.sidebar.title("🔍 篩選條件")
 
st.sidebar.markdown("**類別**")
show_general = st.sidebar.checkbox("🍜 一般美食", value=True)
show_family = st.sidebar.checkbox("👶 親子友善", value=True)
show_pet = st.sidebar.checkbox("🐾 寵物友善", value=True)
 
st.sidebar.markdown("**地區**")
all_areas = ["東區", "北區", "香山區", "竹北市", "竹東鎮", "湖口鄉",
             "新埔鎮", "關西鎮", "新豐鄉", "芎林鄉", "橫山鄉", "北埔鄉", "寶山鄉", "峨眉鄉"]
selected_areas = st.sidebar.multiselect("", options=all_areas, default=["東區"])
 
min_likes = st.sidebar.slider("最低按讚數", 100, 10000, 100, step=100)
 
all_years = ["全部", "2021以前", "2022", "2023", "2024", "2025", "2026"]
selected_years = st.sidebar.multiselect("年份", options=all_years, default=["全部"])
 
all_foods = ["咖啡廳", "甜點冰品", "火鍋", "早午餐", "早餐", "燒烤肉類",
             "麵食", "日式料理", "韓式料理", "西式料理", "海鮮",
             "手搖飲料", "點心麵食", "台式小吃", "東南亞料理", "港式料理", "素食"]
selected_foods = st.sidebar.multiselect("食物類型", options=all_foods, default=all_foods)
 
#  篩選資料 
selected_categories = []
if show_general: selected_categories.append("一般美食")
if show_family: selected_categories.append("親子友善")
if show_pet: selected_categories.append("寵物友善")
 
filtered = food[
    (food["like_count"] >= min_likes) &
    (food["category"].isin(selected_categories)) &
    (food["food_type"].isin(selected_foods))
].copy()
 
if selected_areas:
    filtered = filtered[filtered["area"].isin(selected_areas)]
 
if selected_years and "全部" not in selected_years:
    filtered = filtered[filtered["year_label"].isin(selected_years)]
 
# 標題 
st.title("🗺️ 新竹安心出遊地圖")
st.markdown(f"目前顯示 **{len(filtered)}** 筆美食景點　｜　婦幼安全警示 **{len(safety)}** 筆")
 
#  地圖 
m = folium.Map(location=[24.80, 120.97], zoom_start=13, tiles="Cartodb Positron")
 
# 一般美食
food_group = folium.FeatureGroup(name="🍜 一般美食")
for _, row in filtered[filtered["category"] == "一般美食"].iterrows():
    popup_text = f"""
        <img src="{row['thumbnail']}" width="200"><br>
        <b>{row['display_name']}</b><br>
        📍 {row['address']}<br>
        🍽️ {row['food_type']}<br>
        ❤️ {int(row['like_count'])} likes<br>
        <a href="{row['post_url']}" target="_blank">📸 看原始貼文</a>
    """
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=folium.Popup(popup_text, max_width=250),
        tooltip=row["display_name"],
        icon=folium.Icon(color="blue", icon="cutlery", prefix="fa")
    ).add_to(food_group)
 
# 親子友善
family_group = folium.FeatureGroup(name="👶 親子友善")
for _, row in filtered[filtered["category"] == "親子友善"].iterrows():
    popup_text = f"""
        <img src="{row['thumbnail']}" width="200"><br>
        <b>{row['display_name']}</b><br>
        📍 {row['address']}<br>
        🍽️ {row['food_type']}<br>
        👶 親子友善<br>
        ❤️ {int(row['like_count'])} likes<br>
        <a href="{row['post_url']}" target="_blank">📸 看原始貼文</a>
    """
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=folium.Popup(popup_text, max_width=250),
        tooltip=f"👶 {row['display_name']}",
        icon=folium.Icon(color="green", icon="child", prefix="fa")
    ).add_to(family_group)
 
# 寵物友善
pet_group = folium.FeatureGroup(name="🐾 寵物友善")
for _, row in filtered[filtered["category"] == "寵物友善"].iterrows():
    popup_text = f"""
        <img src="{row['thumbnail']}" width="200"><br>
        <b>{row['display_name']}</b><br>
        📍 {row['address']}<br>
        🍽️ {row['food_type']}<br>
        🐾 寵物友善<br>
        ❤️ {int(row['like_count'])} likes<br>
        <a href="{row['post_url']}" target="_blank">📸 看原始貼文</a>
    """
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=folium.Popup(popup_text, max_width=250),
        tooltip=f"🐾 {row['display_name']}",
        icon=folium.Icon(color="orange", icon="paw", prefix="fa")
    ).add_to(pet_group)
 
# 婦幼安全警示
safety_group = folium.FeatureGroup(name="⚠️ 婦幼安全警示")
HeatMap(
    safety[["lat", "lon"]].values.tolist(),
    radius=40, blur=25,
    gradient={"0.4": "yellow", "0.7": "orange", "1.0": "red"}
).add_to(safety_group)
for _, row in safety.iterrows():
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=folium.Popup(f"🚨 婦幼安全警示地點<br>📍 {row['name']}", max_width=200),
        tooltip=f"🚨 婦幼安全警示｜{row['name']}",
        icon=folium.Icon(color="red", icon="exclamation-sign", prefix="glyphicon")
    ).add_to(safety_group)
 
food_group.add_to(m)
family_group.add_to(m)
pet_group.add_to(m)
safety_group.add_to(m)
folium.LayerControl().add_to(m)
 
st_folium(m, width=1200, height=600)