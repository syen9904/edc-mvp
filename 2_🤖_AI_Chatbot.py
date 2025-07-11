# 檔案: 2_🤖_AI_Chatbot.py
import streamlit as st
import time

# --- 這部分是您的 RAG 後端邏輯 ---
def get_rag_response(patient_id, query):
    # 實際應用中，這裡會呼叫 LangChain/LlamaIndex 的 RAG chain
    # 這裡我們模擬一下
    print(f"Querying for {patient_id} with question: {query}")
    if "血壓" in query:
        return "根據 2025-07-08 的紀錄，病患的血壓是 155/95 mmHg。"
    else:
        return "在病歷中找不到相關資訊。"

st.title("🤖 AI 臨床助理")

# --- 同樣，先選擇病人，以確定 RAG 的搜尋範圍 ---
patient_list = ["Patient_001", "Patient_002", "Patient_003"]
selected_patient = st.sidebar.selectbox("選擇要查詢的病人", patient_list, key="chatbot_patient_select")

if selected_patient:
    st.info(f"您正在查詢 **{selected_patient}** 的資料。")

    # 初始化聊天歷史
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 顯示歷史訊息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 接收使用者輸入
    if prompt := st.chat_input("請問有什麼可以幫您的？ (例如：最近一次的血壓是多少？)"):
        # 將使用者訊息加入歷史並顯示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 產生並顯示 AI 回應
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            # 呼叫您的後端 RAG 函式
            assistant_response = get_rag_response(selected_patient, prompt)
            
            # 模擬打字機效果，增加體驗感
            for chunk in assistant_response.split():
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
        
        # 將 AI 回應加入歷史
        st.session_state.messages.append({"role": "assistant", "content": full_response})
else:
    st.warning("請先在側邊欄選擇一位病人。")