import streamlit as st
import pandas as pd
import os

# --- 1. 設定與資料載入 (Configuration & Data Loading) ---

# 定義包含合成資料的資料夾路徑
DATA_DIR = 'output_data'

@st.cache_data # 使用快取來加速重複載入
def load_data(filename):
    """一個通用的函式，用來從 output_data 資料夾載入 CSV 檔案"""
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        st.error(f"錯誤：找不到資料檔案 '{file_path}'。請先執行 'generate_data.py'。")
        return None
    return pd.read_csv(file_path)

# --- 2. Streamlit 介面佈局 (UI Layout) ---

st.set_page_config(layout="wide", page_title="EMR Viewer")

st.title("🏥 EMR Viewer")
st.markdown("此頁面展示了我們合成的病人資料，作為所有 AI 功能的「事實基礎 (Ground Truth)」。")

# 載入核心資料
patients_df = load_data('patients.csv')
notes_df = load_data('noteevents.csv')

if patients_df is None or notes_df is None:
    st.stop() # 如果資料不存在，停止執行

# --- 側邊欄：病人選擇器 ---
st.sidebar.header("選擇病人")
patient_list = patients_df['subject_id'].tolist()
selected_subject_id = st.sidebar.selectbox(
    "請選擇一位病人以檢視其病歷：",
    options=patient_list,
    index=0,
    format_func=lambda x: f"病人 ID: {x}" # 讓下拉選單顯示更清楚
)

# --- 主畫面：顯示選定病人的資料 ---
if selected_subject_id:
    # 篩選出該病人的基本資料和所有筆記
    patient_details = patients_df[patients_df['subject_id'] == selected_subject_id].iloc[0]
    patient_notes = notes_df[notes_df['subject_id'] == selected_subject_id].copy()
    
    # 將日期欄位轉換為 datetime 物件以便排序
    patient_notes['chart_date'] = pd.to_datetime(patient_notes['chart_date'])
    patient_notes = patient_notes.sort_values(by='chart_date', ascending=False) # 預設按時間倒序，最新的在最上面

    # --- 病人資訊橫幅 (Patient Banner) ---
    # FIX: Changed 'patient_name' to 'subject_id' to match the available data in patients.csv
    st.header(f"病歷總覽：Patient ID {patient_details['subject_id']}")
    
    cols = st.columns(3)
    cols[0].metric("病人 ID (Subject ID)", str(patient_details['subject_id']))
    cols[1].metric("年齡 (Anchor Age)", str(patient_details['anchor_age']))
    cols[2].metric("性別 (Gender)", patient_details['gender'])
    
    st.divider()

    # --- 臨床筆記區 (Clinical Notes Section) ---
    st.subheader("臨床筆記時間軸")

    if not patient_notes.empty:
        for index, note in patient_notes.iterrows():
            # 建立一個資訊豐富的 expander 標題
            expander_title = f"{note['chart_date'].strftime('%Y-%m-%d')} — {note['category']}"
            
            with st.expander(expander_title):
                # 在 expander 內部，顯示完整的筆記內容
                st.text_area(
                    label=f"筆記內容 (Note ID: {note['note_id']})",
                    value=note['text'],
                    height=400,
                    disabled=True, # 設為不可編輯，純展示
                    key=f"note_{note['note_id']}" # 為每個 text_area 提供唯一的 key
                )
    else:
        st.info("這位病人沒有任何臨床筆記記錄。")

else:
    st.warning("請從左側邊欄選擇一位病人。")
