import os
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- 1. 設定區 (Configuration) ---
ARCHETYPE_DIR = 'hcc_trial_cohort'
PROMPT_TEMPLATE_DIR = 'prompt_templates' # 新增：提示模板資料夾
OUTPUT_DIR = 'output_data'
START_DATE = "2018-01-01"
SIMULATION_YEARS = 5

# --- 2. 核心類別與函式 (Core Classes & Functions) ---

class PromptManager:
    """
    管理並格式化所有從外部檔案載入的提示模板。
    """
    def __init__(self, template_dir):
        self.template_dir = template_dir
        self.templates = {}
        self._load_templates()
        print(f"Loaded {len(self.templates)} prompt templates.")

    def _load_templates(self):
        """從資料夾載入所有 .txt 模板檔案"""
        if not os.path.exists(self.template_dir):
            raise FileNotFoundError(f"Prompt template directory not found: '{self.template_dir}'")
        for filename in os.listdir(self.template_dir):
            if filename.endswith(".txt"):
                name = filename.split('.')[0]
                with open(os.path.join(self.template_dir, filename), 'r', encoding='utf-8') as f:
                    self.templates[name] = f.read()

    def get_prompt(self, name, **context):
        """
        根據名稱獲取模板，並填入上下文變數。
        e.g., get_prompt('clinic_note', age=65, gender='Male', ...)
        """
        template = self.templates.get(name)
        if not template:
            raise ValueError(f"Template '{name}' not found.")
        return template.format(**context)

def load_archetypes(path):
    """從指定路徑載入所有 YAML 原型檔案"""
    archetypes = {}
    print(f"Loading archetypes from: {path}")
    for filename in os.listdir(path):
        if filename.endswith(".yml") or filename.endswith(".yaml"):
            archetype_name = filename.split('.')[0]
            with open(os.path.join(path, filename), 'r', encoding='utf-8') as f:
                archetypes[archetype_name] = yaml.safe_load(f)
    print(f"Loaded {len(archetypes)} archetypes.")
    return archetypes

def simulate_health_trajectory(archetype, start_date, years):
    """根據原型模擬病人的隱藏健康軌跡"""
    end_date = pd.to_datetime(start_date) + pd.DateOffset(years=years)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    trajectory = pd.DataFrame(index=dates)

    for param, config in archetype.get('health_parameters', {}).items():
        values = []
        current_value = config['baseline']
        daily_drift = config.get('yearly_drift', 0) / 365.0
        volatility = config.get('volatility', 0)
        
        for _ in range(len(dates)):
            random_shock = np.random.normal(0, volatility / np.sqrt(30)) if volatility > 0 else 0
            current_value += daily_drift + random_shock
            values.append(current_value)
        
        trajectory[f"underlying_{param}"] = values
    return trajectory

def trigger_events(trajectory, archetype):
    """在時間軸上觸發臨床事件"""
    events = []
    max_date = trajectory.index.max()
    for month_start in pd.date_range(start=trajectory.index.min(), end=max_date, freq='MS'):
        for event_type, probability in archetype.get('event_probabilities_per_month', {}).items():
            if np.random.rand() < probability:
                event_day = month_start + timedelta(days=np.random.randint(0, 28))
                # FIX 1: Ensure the generated event date is within the simulation time frame.
                if event_day <= max_date:
                    events.append({'date': event_day, 'event_type': event_type})
    
    if archetype.get('trial_specific_criteria', {}).get('history_of_major_gi_bleed_last_2_months', False):
        screening_date = trajectory.index.max()
        bleed_date = screening_date - timedelta(days=np.random.randint(20, 50)) # 在篩選前1-2個月內發生
        if bleed_date >= trajectory.index.min():
             events.append({'date': bleed_date, 'event_type': 'hospitalization_gi_bleed'})

    return pd.DataFrame(events).sort_values(by='date').reset_index(drop=True)

class NoteGenerator:
    """
    生成臨床筆記的核心類別。
    它使用 PromptManager 來獲取模板，而不是硬編碼。
    """
    def __init__(self, archetype, trajectory, prompt_manager):
        self.archetype = archetype
        self.trajectory = trajectory
        self.prompt_manager = prompt_manager
        self.note_id_counter = 1

    def _get_context(self, event_date):
        """為特定事件建立上下文"""
        context = self.archetype['demographics'].copy()
        context['patient_name'] = self.archetype['name']
        context['date'] = event_date.strftime('%Y-%m-%d')
        context['chronic_conditions'] = ", ".join(self.archetype['chronic_conditions'])
        
        for param, config in self.archetype.get('health_parameters', {}).items():
            # Ensure the lookup date is valid before accessing .loc
            lookup_date = event_date if event_date in self.trajectory.index else self.trajectory.index.asof(event_date)
            underlying_val = self.trajectory.loc[lookup_date][f"underlying_{param}"]
            measurement_error = np.random.normal(0, config['volatility'] * 0.1)
            context[f"measured_{param}"] = round(underlying_val + measurement_error, 2)
        
        # 增加一個簡單的文字描述，讓筆記更生動
        context['renal_function_text'] = 'stable' if context.get('measured_creatinine', 0) <= 2.0 else 'notably elevated, a concern for trial eligibility'
        return context

    def generate_note_for_event(self, event):
        """根據事件類型生成筆記"""
        event_date = event['date']
        event_type = event['event_type']
        context = self._get_context(event_date)
        
        note_text = ""
        note_category = "Unknown"
        template_name = ""

        if event_type == 'oncology_clinic_visit':
            note_category = "Oncology Clinic Note"
            template_name = "clinic_note"
        elif event_type == 'imaging_mri_abdomen':
            note_category = "Radiology Report"
            template_name = "radiology_report"
            # FIX 2: Make note generation robust. If a parameter is missing, provide a default.
            if 'measured_tumor_size_cm' not in context:
                context['measured_tumor_size_cm'] = '[not applicable for this patient]'
        elif event_type == 'hospitalization_gi_bleed':
            note_category = "Discharge Summary"
            template_name = "discharge_summary_gi_bleed"
            # 為出院總結增加額外上下文
            context['admission_date'] = (pd.to_datetime(context['date']) - timedelta(days=4)).strftime('%Y-%m-%d')

        if template_name:
            try:
                note_text = self.prompt_manager.get_prompt(template_name, **context)
                note = {
                    'note_id': self.note_id_counter,
                    'chart_date': event_date.strftime('%Y-%m-%d'),
                    'category': note_category,
                    'text': note_text
                }
                self.note_id_counter += 1
                return note
            except Exception as e:
                print(f"Could not generate note for template '{template_name}': {e}")
        
        return None

# --- 3. 主執行流程 (Main Execution Flow) ---
def main():
    """主函式，執行整個資料生成流程"""
    print("--- Starting Synthetic Data Generation ---")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    try:
        archetypes = load_archetypes(ARCHETYPE_DIR)
        prompt_manager = PromptManager(PROMPT_TEMPLATE_DIR)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure 'hcc_trial_cohort' and 'prompt_templates' directories exist.")
        return

    all_patients_data = []
    all_notes_data = []
    
    subject_id_start = 10000000

    for i, (name, archetype) in enumerate(archetypes.items()):
        subject_id = subject_id_start + i
        print(f"\nProcessing patient {subject_id} from archetype: {name}...")

        patient_info = archetype['demographics'].copy()
        patient_info['subject_id'] = subject_id
        all_patients_data.append(patient_info)

        trajectory = simulate_health_trajectory(archetype, START_DATE, SIMULATION_YEARS)
        events = trigger_events(trajectory, archetype)
        print(f"Generated {len(events)} clinical events.")

        note_generator = NoteGenerator(archetype, trajectory, prompt_manager)
        patient_notes = []
        for _, event in events.iterrows():
            note = note_generator.generate_note_for_event(event)
            if note:
                note['subject_id'] = subject_id
                patient_notes.append(note)
        
        all_notes_data.extend(patient_notes)
        print(f"Generated {len(patient_notes)} clinical notes for patient {subject_id}.")

    patients_df = pd.DataFrame(all_patients_data)
    notes_df = pd.DataFrame(all_notes_data)

    # 移除壓縮，直接儲存為 .csv
    patients_path = os.path.join(OUTPUT_DIR, 'patients.csv')
    notes_path = os.path.join(OUTPUT_DIR, 'noteevents.csv')

    patients_df.to_csv(patients_path, index=False)
    notes_df.to_csv(notes_path, index=False)

    print("\n--- Synthetic Data Generation Complete ---")
    print(f"Generated data for {len(all_patients_data)} patients.")
    print(f"Total clinical notes created: {len(all_notes_data)}")
    print(f"Output files saved to '{OUTPUT_DIR}' directory:")
    print(f"- {os.path.basename(patients_path)}")
    print(f"- {os.path.basename(notes_path)}")

if __name__ == '__main__':
    main()
