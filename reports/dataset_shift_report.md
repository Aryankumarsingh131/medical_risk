# Adversarial Dataset Shift Analysis Report

- **Domain Classifier Accuracy**: `94.74%`
- **Majority-Class Baseline**: `54.06%`
- **Verdict**: **datasets show significant distribution shift, consider training separate models or adding a domain-adaptation step.**

## Top Features Driving Domain Separation

| Feature | Feature Importance (%) |
| :--- | :---: |
| `movement` | 18.57% |
| `chest_pain_type` | 18.23% |
| `bmi` | 17.17% |
| `hypertension` | 10.34% |
| `sex` | 8.41% |
| `fasting_blood_sugar` | 5.38% |
| `smoking` | 4.85% |
| `resting_bp` | 4.34% |
| `age` | 3.57% |
| `cholesterol` | 2.50% |
| `max_heart_rate` | 2.34% |
| `alcohol` | 1.58% |
| `prior_medical_events` | 1.39% |
| `diabetes` | 1.25% |
| `current_medication_list` | 0.03% |
| `st_depression` | 0.02% |
| `exercise_angina` | 0.02% |
| `temperature` | 0.00% |
| `drug` | 0.00% |
| `speech` | 0.00% |
| `active_diagnosis` | 0.00% |
