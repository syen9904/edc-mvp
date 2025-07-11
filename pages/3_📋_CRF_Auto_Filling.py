# 檔案: 3_📋_CRF_Auto_Filling.py
import streamlit as st
import json

# --- 模擬後端抽取函式 ---
def extract_crf_data(patient_id, crf_field):
    # 這裡會呼叫您的 LLM 抽取鏈
    # 返回一個包含答案和來源的 dict
    query = crf_field['query']
    print(f"Extracting for {patient_id}, field: {crf_field['label']}, query: {query}")
    if "HbA1c" in query:
        return {"answer": "Not Found in recent note", "source": "No recent HbA1c test mentioned."}
    if "Systolic Blood Pressure" in query:
        return {"answer": "155", "source": "O: BP 155/95 mmHg, Fasting Sugar 160 mg/dL."}
    if "medication changes" in query:
        return {"answer": "Yes, Amlodipine dose was adjusted.", "source": "P: 調整降血壓藥物為 Amlodipine 10mg QD..."}
    return {"answer": None, "source": None}


st.title("📝 CRF 一鍵自動填寫")

# --- 同樣，先選擇病人 ---
patient_list = ["Patient_001", "Patient_002", "Patient_003"]
selected_patient = st.sidebar.selectbox("選擇要填寫表單的病人", patient_list, key="crf_patient_select")

if selected_patient:
    st.info(f"您正在為 **{selected_patient}** 填寫 CRF。")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("CRF 定義 (JSON)")
        crf_template_str = st.text_area("CRF Template", value="""
{
  "form_name": "Diabetes Follow-Up",
  "fields": [
    {"id": "bp_systolic", "label": "Latest Systolic Blood Pressure", "query": "What is the most recent systolic blood pressure?"},
    {"id": "hba1c", "label": "Latest HbA1c Value", "query": "What is the latest HbA1c value?"},
    {"id": "med_change", "label": "Recent Medication Changes", "query": "Were there any recent medication changes?"}
  ]
}
        """, height=300)

    with col2:
        st.subheader("自動填寫結果")
        if st.button("🚀 一鍵填寫表單"):
            try:
                crf_template = json.loads(crf_template_str)
                with st.spinner("AI 正在分析病歷並填寫表單..."):
                    results = []
                    for field in crf_template['fields']:
                        result = extract_crf_data(selected_patient, field)
                        results.append({"label": field['label'], **result})
                
                st.success("表單填寫完成！")

                for res in results:
                    st.markdown(f"**{res['label']}**")
                    if res['answer'] and "Not Found" not in res['answer']:
                        st.text_input("結果", value=res['answer'], disabled=True, key=res['label'])
                        with st.expander("點此查看資料來源 (Supporting Source)"):
                            st.info(f"來源內文: \"{res['source']}\"")
                    else:
                        st.warning("在病歷中未找到相關資料。")
                    st.divider()

            except json.JSONDecodeError:
                st.error("CRF 定義的 JSON 格式有誤，請檢查。")

else:
    st.warning("請先在側邊欄選擇一位病人。")