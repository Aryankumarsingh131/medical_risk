# Dataset Inventory & Diagnostic Comparison

Comprehensive health-check across all raw datasets in `data/raw/` comparing shape, feature composition (numeric vs categorical), memory footprint, duplicates, target distribution, class imbalance ratio, outlier counts, and missingness.

| Dataset | Rows | Total Feat | Num / Cat | Memory | Duplicates | Target Name | Target Type | Imbalance | Outliers | Missing % |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- | :---: | :---: | :---: |
| `Covid Data.csv` | 1,048,575 | 20 | 19 / 1 | 219.0 MB | 812,049 | `DIABETES` | Multiclass (3) | 275.69:1 | 5,640 | 0.0% |
| `data.csv` | 800 | 19 | 18 / 1 | 0.15 MB | 0 | `N/A` | None | N/A | 121 | 0.0% |
| `diabetes_012_health_indicators_BRFSS2015.csv` | 253,680 | 21 | 21 / 0 | 42.58 MB | 23,899 | `Diabetes_012` | Multiclass (3) | 46.15:1 | 99,085 | 0.0% |
| `diabetes_binary_5050split_health_indicators_BRFSS2015.csv` | 70,692 | 21 | 21 / 0 | 11.87 MB | 1,635 | `Diabetes_binary` | Binary | 1.00:1 | 24,621 | 0.0% |
| `diabetes_binary_health_indicators_BRFSS2015.csv` | 253,680 | 21 | 21 / 0 | 42.58 MB | 24,206 | `Diabetes_binary` | Binary | 6.18:1 | 99,085 | 0.0% |
| `diabetes_prediction_dataset.csv` | 100,000 | 8 | 6 / 2 | 15.78 MB | 3,854 | `heart_disease` | Binary | 24.37:1 | 10,439 | 0.0% |
| `drugs_side_effects_drugs_com.csv` | 2,931 | 16 | 2 / 14 | 18.04 MB | 0 | `medical_condition` | Categorical (47) | 52.80:1 | 282 | 14.86% |
| `estimated_numbers.csv` | 856 | 10 | 7 / 3 | 0.24 MB | 0 | `WHO Region` | Multiclass (6) | 4.78:1 | 405 | 13.68% |
| `framingham_heart_study.csv` | 4,240 | 15 | 15 / 0 | 0.52 MB | 0 | `TenYearCHD` | Binary | 5.58:1 | 632 | 0.95% |
| `Health_Risk_Dataset.csv` | 1,000 | 9 | 7 / 2 | 0.2 MB | 0 | `Risk_Level` | Multiclass (4) | 1.91:1 | 57 | 0.0% |
| `Heart_disease_cleveland_new.csv` | 303 | 13 | 13 / 0 | 0.03 MB | 0 | `target` | Binary | 1.18:1 | 63 | 0.0% |
| `Heart_Disease_Prediction.csv` | 270 | 13 | 13 / 0 | 0.04 MB | 0 | `Heart Disease` | Binary | 1.25:1 | 58 | 0.0% |
| `heart_failure_clinical_records_dataset.csv` | 299 | 12 | 12 / 0 | 0.03 MB | 0 | `DEATH_EVENT` | Binary | 2.11:1 | 85 | 0.0% |
| `incidence_per_1000_pop_at_risk.csv` | 2,033 | 3 | 2 / 1 | 0.26 MB | 0 | `WHO Region` | Multiclass (6) | 4.78:1 | 34 | 0.0% |
| `osteoporosis.csv` | 1,958 | 15 | 2 / 13 | 1.36 MB | 0 | `Osteoporosis` | Binary | 1.00:1 | 0 | 8.36% |
| `reported_numbers.csv` | 1,944 | 4 | 3 / 1 | 0.26 MB | 0 | `WHO Region` | Multiclass (6) | 4.89:1 | 592 | 5.17% |
| `stroke_risk_dataset.csv` | 70,000 | 17 | 17 / 0 | 9.61 MB | 1,021 | `Stroke Risk (%)` | Continuous | 991.00:1 | 72 | 0.0% |
| `The_Cancer_data_1500_V2.csv` | 1,500 | 8 | 8 / 0 | 0.1 MB | 0 | `Diagnosis` | Binary | 1.69:1 | 0 | 0.0% |
| `cardiovascular.txt` | 462 | 10 | 9 / 1 | 0.06 MB | 0 | `chd` | Binary | 1.89:1 | 94 | 0.0% |
