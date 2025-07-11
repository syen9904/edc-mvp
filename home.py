import streamlit as st

st.set_page_config(page_title="EHR to EDC Demo")

st.title("🏠 病人總覽與選擇")
st.markdown("請在下方選擇一位病人，然後您可以從左側導覽列切換到其他功能頁面。")

# --- 初始化 session_state 中的 key ---
if 'selected_patient' not in st.session_state:
    st.session_state.selected_patient = None

# --- 病人選擇器 ---
patient_list = ["Patient_001", "Patient_002", "Patient_003"]
# 當 selectbox 的值改變時，會自動更新 st.session_state.selected_patient
st.selectbox(
    "選擇病人",
    patient_list,
    key='selected_patient', # 將這個 widget 的狀態直接綁定到 session_state 的 'selected_patient' key
    index=None, # 預設不選擇任何項目
    placeholder="請選擇一位病人..."
)

# 顯示當前選擇的病人是誰
if st.session_state.selected_patient:
    st.success(f"您已選擇病人: **{st.session_state.selected_patient}**。現在可以去其他頁面進行操作了。")
else:
    st.info("請先選擇一位病人。")