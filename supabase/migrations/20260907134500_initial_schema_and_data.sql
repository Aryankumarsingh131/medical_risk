-- Supabase migration: Schema and initial data

-- Drop tables

DROP TABLE IF EXISTS patient_registration_requests CASCADE;
DROP TABLE IF EXISTS medicines CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS blood_test_results CASCADE;
DROP TABLE IF EXISTS patient_assessments CASCADE;
DROP TABLE IF EXISTS clinical_drafts CASCADE;
DROP TABLE IF EXISTS doctor_diagnoses CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS prediction_logs CASCADE;


-- Create tables

CREATE TABLE hospitals (
	id SERIAL NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	address VARCHAR(255) NOT NULL, 
	contact_number VARCHAR(30) NOT NULL, 
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	available_beds INTEGER, 
	icu_beds_available INTEGER, 
	ventilators_available INTEGER, 
	blood_bank_available BOOLEAN, 
	emergency_services_available BOOLEAN, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE prediction_logs (
	id SERIAL NOT NULL, 
	patient_id VARCHAR(100), 
	risk_score FLOAT NOT NULL, 
	risk_label VARCHAR(20) NOT NULL, 
	model_version VARCHAR(50) NOT NULL, 
	predicted_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	name VARCHAR(100), 
	email VARCHAR(120) NOT NULL, 
	hashed_password VARCHAR NOT NULL, 
	role VARCHAR(20), 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	specialization VARCHAR(100), 
	license_number VARCHAR(50), 
	degree VARCHAR(150), 
	years_of_experience INTEGER, 
	certifications TEXT, 
	doctor_id INTEGER, 
	age FLOAT, 
	sex FLOAT, 
	is_demographics_locked BOOLEAN, 
	phone_number VARCHAR(30), 
	emergency_contact_name VARCHAR(100), 
	emergency_contact_phone VARCHAR(30), 
	address VARCHAR(255), 
	pending_assignment BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(doctor_id) REFERENCES users (id)
);

CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	actor_user_id INTEGER, 
	actor_role VARCHAR(20) NOT NULL, 
	action VARCHAR(60) NOT NULL, 
	target_type VARCHAR(50), 
	target_id INTEGER, 
	details TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_user_id) REFERENCES users (id)
);

CREATE TABLE blood_test_results (
	id SERIAL NOT NULL, 
	patient_id INTEGER NOT NULL, 
	recorded_by_doctor_id INTEGER, 
	hemoglobin FLOAT, 
	wbc_count FLOAT, 
	platelet_count FLOAT, 
	fasting_glucose FLOAT, 
	hba1c FLOAT, 
	total_cholesterol FLOAT, 
	hdl FLOAT, 
	ldl FLOAT, 
	triglycerides FLOAT, 
	creatinine FLOAT, 
	notes TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES users (id), 
	FOREIGN KEY(recorded_by_doctor_id) REFERENCES users (id)
);

CREATE TABLE clinical_drafts (
	id SERIAL NOT NULL, 
	doctor_id INTEGER NOT NULL, 
	draft_name VARCHAR(100), 
	guest_identifier VARCHAR(100), 
	raw_data_json TEXT NOT NULL, 
	risk_level VARCHAR(30), 
	risk_probability FLOAT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(doctor_id) REFERENCES users (id)
);

CREATE TABLE doctor_diagnoses (
	id SERIAL NOT NULL, 
	patient_id INTEGER NOT NULL, 
	doctor_id INTEGER NOT NULL, 
	diagnosis_title VARCHAR(200) NOT NULL, 
	clinical_notes TEXT NOT NULL, 
	treatment_plan TEXT, 
	prescriptions TEXT, 
	risk_summary VARCHAR(150), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES users (id), 
	FOREIGN KEY(doctor_id) REFERENCES users (id)
);

CREATE TABLE hospital_availability (
	id SERIAL NOT NULL, 
	hospital_id INTEGER NOT NULL, 
	availability_status VARCHAR(50), 
	available_beds INTEGER, 
	icu_beds_available INTEGER, 
	ventilators_available INTEGER, 
	blood_bank_available BOOLEAN, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(hospital_id) REFERENCES hospitals (id)
);

CREATE TABLE hospital_doctor_availability (
	id SERIAL NOT NULL, 
	hospital_id INTEGER NOT NULL, 
	specialization VARCHAR(100) NOT NULL, 
	available_doctors INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(hospital_id) REFERENCES hospitals (id)
);

CREATE TABLE medicines (
	id SERIAL NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	generic_name VARCHAR(150), 
	category VARCHAR(100), 
	unit VARCHAR(30), 
	quantity INTEGER, 
	requested_by_doctor_id INTEGER, 
	doctor_id INTEGER, 
	status VARCHAR(30), 
	notes TEXT, 
	requested_at TIMESTAMP WITHOUT TIME ZONE, 
	procured_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(requested_by_doctor_id) REFERENCES users (id), 
	FOREIGN KEY(doctor_id) REFERENCES users (id)
);

CREATE TABLE patient_assessments (
	id SERIAL NOT NULL, 
	patient_id INTEGER NOT NULL, 
	doctor_id INTEGER, 
	age FLOAT, 
	sex FLOAT, 
	systolic_bp INTEGER, 
	diastolic_bp INTEGER, 
	max_heart_rate FLOAT, 
	bmi FLOAT, 
	cholesterol FLOAT, 
	fasting_blood_sugar FLOAT, 
	st_depression FLOAT, 
	chest_pain_type FLOAT, 
	exercise_angina FLOAT, 
	hypertension FLOAT, 
	diabetes FLOAT, 
	smoking FLOAT, 
	prior_medical_events VARCHAR(255), 
	risk_level VARCHAR(30) NOT NULL, 
	risk_probability FLOAT NOT NULL, 
	triggered_rule_codes TEXT, 
	clinical_recommendations TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES users (id), 
	FOREIGN KEY(doctor_id) REFERENCES users (id)
);

CREATE TABLE patient_registration_requests (
	id SERIAL NOT NULL, 
	patient_id INTEGER NOT NULL, 
	preferred_doctor_id INTEGER, 
	department_preference VARCHAR(100), 
	status VARCHAR(20), 
	notes TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES users (id), 
	FOREIGN KEY(preferred_doctor_id) REFERENCES users (id)
);

-- Insert data

-- Data for users
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (1, 'Admin', 'admin@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'admin', TRUE, '2026-09-07 10:03:53.964352', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, FALSE, NULL, NULL, NULL, NULL, FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (2, 'Dr. Sharma', 'dr.sharma@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'doctor', TRUE, '2026-09-07 10:03:53.979289', 'Cardiology', 'DOC-IN-101', 'MBBS, MD (Cardiology), FACC', 14, 'Board Certified Cardiologist, ACLS Certified, Fellow of the American College of Cardiology', NULL, NULL, NULL, FALSE, NULL, NULL, NULL, NULL, FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (3, 'Dr. Mehta', 'dr.mehta@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'doctor', TRUE, '2026-09-07 10:03:54.011061', 'Internal Medicine', 'DOC-IN-102', 'MBBS, MD (General Medicine)', 11, 'Board Certified Internal Physician, Advanced Diabetes Specialist', NULL, NULL, NULL, FALSE, NULL, NULL, NULL, NULL, FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (4, 'Dr. Khan', 'dr.khan@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'doctor', TRUE, '2026-09-07 10:03:54.043246', 'Endocrinology', 'DOC-IN-103', 'MBBS, MD, DM (Endocrinology)', 9, 'Endocrine Society Fellow, Certified Thyroid & Metabolic Specialist', NULL, NULL, NULL, FALSE, NULL, NULL, NULL, NULL, FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (5, 'Dr. Rao', 'dr.rao@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'doctor', TRUE, '2026-09-07 10:03:54.078846', 'Pulmonology', 'DOC-IN-104', 'MBBS, DNB (Respiratory Medicine)', 12, 'FCCCP, Critical Care Pulmonologist', NULL, NULL, NULL, FALSE, NULL, NULL, NULL, NULL, FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (6, 'Dr. Iyer', 'dr.iyer@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'doctor', TRUE, '2026-09-07 10:03:54.111126', 'Nephrology', 'DOC-IN-105', 'MBBS, MD, DM (Nephrology)', 15, 'Renal Transplant Specialist, Dialysis Director Certification', NULL, NULL, NULL, FALSE, NULL, NULL, NULL, NULL, FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (7, 'Arjun', 'patient.arjun@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:03:54.142879', NULL, NULL, NULL, NULL, NULL, 2, 11.0, 1.0, TRUE, '+91 98765 43211', 'Emergency Contact 1', '+91 98765 43221', 'Address 1, Medical District', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (8, 'Riya', 'patient.riya@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:03:54.228760', NULL, NULL, NULL, NULL, NULL, 3, 47.0, 0.0, TRUE, '+91 98765 43212', 'Emergency Contact 2', '+91 98765 43222', 'Address 2, Medical District', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (9, 'Rohan', 'patient.rohan@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:03:54.458761', NULL, NULL, NULL, NULL, NULL, 4, 47.0, 1.0, TRUE, '+91 98765 43213', 'Emergency Contact 3', '+91 98765 43223', 'Address 3, Medical District', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (10, 'Ananya', 'patient.ananya@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:03:54.516870', NULL, NULL, NULL, NULL, NULL, 5, 80.0, 0.0, TRUE, '+91 98765 43214', 'Emergency Contact 4', '+91 98765 43224', 'Address 4, Medical District', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (11, 'Vikram', 'patient.vikram@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:03:54.574607', NULL, NULL, NULL, NULL, NULL, 6, 37.0, 1.0, TRUE, '+91 98765 43215', 'Emergency Contact 5', '+91 98765 43225', 'Address 5, Medical District', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (12, 'Pooja', 'patient.pooja@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:03:54.634773', NULL, NULL, NULL, NULL, NULL, 2, 47.0, 0.0, TRUE, '+91 98765 43216', 'Emergency Contact 6', '+91 98765 43226', 'Address 6, Medical District', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (13, 'Siddharth', 'patient.siddharth@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:03:54.693528', NULL, NULL, NULL, NULL, NULL, 3, 36.0, 1.0, TRUE, '+91 98765 43217', 'Emergency Contact 7', '+91 98765 43227', 'Address 7, Medical District', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (14, 'Neha', 'patient.neha@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:03:54.754089', NULL, NULL, NULL, NULL, NULL, 4, 4.0, 0.0, TRUE, '+91 98765 43218', 'Emergency Contact 8', '+91 98765 43228', 'Address 8, Medical District', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (15, 'Aditya', 'patient.aditya@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:03:54.812211', NULL, NULL, NULL, NULL, NULL, 5, 12.0, 1.0, TRUE, '+91 98765 43219', 'Emergency Contact 9', '+91 98765 43229', 'Address 9, Medical District', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (16, 'Kavya', 'patient.kavya@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:03:54.873683', NULL, NULL, NULL, NULL, NULL, 6, 41.0, 0.0, TRUE, '+91 98765 43220', 'Emergency Contact 10', '+91 98765 43230', 'Address 10, Medical District', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (17, 'Priya Guest Registered', 'priya.guest.registered@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:04:22.795898', NULL, NULL, NULL, NULL, NULL, 2, 54.0, 1.0, TRUE, '+91 9988776655', 'Ravi', '+91 9988776654', 'Indiranagar, Bangalore', FALSE);
INSERT INTO users (id, name, email, hashed_password, role, is_active, created_at, specialization, license_number, degree, years_of_experience, certifications, doctor_id, age, sex, is_demographics_locked, phone_number, emergency_contact_name, emergency_contact_phone, address, pending_assignment) VALUES (18, 'New Walkin Patient', 'selfreg.patient@hospital.com', '38d03418c28cf7c45f73f90b0ceabef2c661076103b3327abd6f410ceeb952bb', 'patient', TRUE, '2026-09-07 10:04:22.833323', NULL, NULL, NULL, NULL, NULL, 3, NULL, NULL, FALSE, NULL, NULL, NULL, NULL, FALSE);
SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE((SELECT MAX(id) FROM users), 1));

-- Data for doctor_diagnoses
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (1, 7, 2, 'Routine Preventative Cardiovascular Screening', 'Patient evaluated in clinic with resting BP 120/80.0 mmHg and BMI 25.0. Family history notes Not specified in dataset. Recommended continuous monitoring.', 'Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks.', 'Multivitamin daily, lifestyle modification', 'Risk Score 27.1% (Moderate Risk)', '2026-09-07 10:03:54.215355', '2026-09-07 10:03:54.215361');
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (2, 8, 3, 'Routine Preventative Cardiovascular Screening', 'Patient evaluated in clinic with resting BP 120/80.0 mmHg and BMI 25.0. Family history notes Not specified in dataset. Recommended continuous monitoring.', 'Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks.', 'Multivitamin daily, lifestyle modification', 'Risk Score 42.9% (High Risk)', '2026-09-07 10:03:54.446874', '2026-09-07 10:03:54.446879');
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (3, 9, 4, 'Stage 1 Essential Hypertension with Moderate Atherogenic Risk', 'Patient evaluated in clinic with resting BP 154.0/80.0 mmHg and BMI 28.23. Family history notes Not specified in dataset. Recommended continuous monitoring.', 'Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks.', 'Amlodipine 5mg OD, Atorvastatin 10mg HS (if lipid profile indicates)', 'Risk Score 58.6% (High Risk)', '2026-09-07 10:03:54.506083', '2026-09-07 10:03:54.506092');
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (4, 10, 5, 'Routine Preventative Cardiovascular Screening', 'Patient evaluated in clinic with resting BP 120/80.0 mmHg and BMI 27.32. Family history notes Not specified in dataset. Recommended continuous monitoring.', 'Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks.', 'Multivitamin daily, lifestyle modification', 'Risk Score 52.9% (High Risk)', '2026-09-07 10:03:54.564444', '2026-09-07 10:03:54.564450');
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (5, 11, 6, 'Routine Preventative Cardiovascular Screening', 'Patient evaluated in clinic with resting BP 120/80.0 mmHg and BMI 25.0. Family history notes Not specified in dataset. Recommended continuous monitoring.', 'Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks.', 'Multivitamin daily, lifestyle modification', 'Risk Score 27.1% (Moderate Risk)', '2026-09-07 10:03:54.624096', '2026-09-07 10:03:54.624102');
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (6, 12, 2, 'Routine Preventative Cardiovascular Screening', 'Patient evaluated in clinic with resting BP 120/80.0 mmHg and BMI 25.0. Family history notes Not specified in dataset. Recommended continuous monitoring.', 'Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks.', 'Multivitamin daily, lifestyle modification', 'Risk Score 37.1% (Moderate Risk)', '2026-09-07 10:03:54.682453', '2026-09-07 10:03:54.682459');
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (7, 13, 3, 'Routine Preventative Cardiovascular Screening', 'Patient evaluated in clinic with resting BP 120/80.0 mmHg and BMI 24.52. Family history notes Not specified in dataset. Recommended continuous monitoring.', 'Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks.', 'Multivitamin daily, lifestyle modification', 'Risk Score 37.1% (Moderate Risk)', '2026-09-07 10:03:54.742918', '2026-09-07 10:03:54.742923');
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (8, 14, 4, 'Routine Preventative Cardiovascular Screening', 'Patient evaluated in clinic with resting BP 120/80.0 mmHg and BMI 25.0. Family history notes Not specified in dataset. Recommended continuous monitoring.', 'Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks.', 'Multivitamin daily, lifestyle modification', 'Risk Score 27.1% (Moderate Risk)', '2026-09-07 10:03:54.802329', '2026-09-07 10:03:54.802334');
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (9, 15, 5, 'Routine Preventative Cardiovascular Screening', 'Patient evaluated in clinic with resting BP 120/80.0 mmHg and BMI 27.32. Family history notes Not specified in dataset. Recommended continuous monitoring.', 'Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks.', 'Multivitamin daily, lifestyle modification', 'Risk Score 58.6% (High Risk)', '2026-09-07 10:03:54.862799', '2026-09-07 10:03:54.862804');
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (10, 16, 6, 'Routine Preventative Cardiovascular Screening', 'Patient evaluated in clinic with resting BP 120/80.0 mmHg and BMI 27.32. Family history notes Not specified in dataset. Recommended continuous monitoring.', 'Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks.', 'Multivitamin daily, lifestyle modification', 'Risk Score 58.6% (High Risk)', '2026-09-07 10:03:54.918517', '2026-09-07 10:03:54.918523');
INSERT INTO doctor_diagnoses (id, patient_id, doctor_id, diagnosis_title, clinical_notes, treatment_plan, prescriptions, risk_summary, created_at, updated_at) VALUES (11, 7, 3, 'Atherosclerotic Vascular Evaluation', 'Patient referred from Cardiology. Vitals stable under current statin regimen.', 'Continue DASH dietary protocol, periodic blood panel in 3 months.', 'Atorvastatin 10mg HS, Aspirin 75mg OD', 'Moderate Risk (45.0%)', '2026-09-07 10:04:22.665344', '2026-09-07 10:04:22.665362');
SELECT setval(pg_get_serial_sequence('doctor_diagnoses', 'id'), COALESCE((SELECT MAX(id) FROM doctor_diagnoses), 1));

-- Data for patient_assessments
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (1, 7, 2, 37.0, 1.0, 120, 80, 150.0, 25.0, 200.0, 0.0, NULL, NULL, NULL, NULL, NULL, 0.0, NULL, 'Moderate Risk', 0.2714, '["bp_stage1", "chol_borderline", "bmi_overweight"]', '[]', '2026-09-07 10:03:54.181993');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (2, 8, 3, 68.0, 0.0, 120, 80, 150.0, 25.0, 200.0, 0.0, NULL, NULL, NULL, NULL, NULL, 0.0, NULL, 'High Risk', 0.4286, '["age_senior", "bp_stage1", "chol_borderline", "bmi_overweight"]', '[]', '2026-09-07 10:03:54.259493');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (3, 9, 4, 46.0, 1.0, 154, 80, 75.0, 28.23, 230.0, 0.0, NULL, NULL, NULL, NULL, NULL, 0.0, NULL, 'High Risk', 0.5857, '["bp_stage2", "hr_chronotropic_incompetence", "chol_borderline", "bmi_overweight", "age_adult"]', '[]', '2026-09-07 10:03:54.479555');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (4, 10, 5, 80.0, 0.0, 120, 80, 150.0, 27.32, 200.0, 0.0, NULL, NULL, NULL, NULL, NULL, 0.0, NULL, 'High Risk', 0.5286, '["age_senior", "bp_stage1", "hr_excessive_tachycardia", "chol_borderline", "bmi_overweight"]', '[]', '2026-09-07 10:03:54.536348');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (5, 11, 6, 30.0, 1.0, 120, 80, 150.0, 25.0, 200.0, 0.0, NULL, NULL, NULL, NULL, NULL, 0.0, NULL, 'Moderate Risk', 0.2714, '["bp_stage1", "chol_borderline", "bmi_overweight"]', '[]', '2026-09-07 10:03:54.597064');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (6, 12, 2, 51.0, 0.0, 120, 80, 150.0, 25.0, 200.0, 0.0, NULL, NULL, NULL, NULL, NULL, 0.0, NULL, 'Moderate Risk', 0.3714, '["bp_stage1", "age_middle", "chol_borderline", "bmi_overweight"]', '[]', '2026-09-07 10:03:54.654523');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (7, 13, 3, 26.0, 1.0, 120, 80, 150.0, 24.52, 200.0, 0.0, NULL, NULL, NULL, NULL, NULL, 1.0, NULL, 'Moderate Risk', 0.3714, '["smoking", "bp_stage1", "chol_borderline"]', '[]', '2026-09-07 10:03:54.714859');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (8, 14, 4, 20.0, 0.0, 120, 80, 150.0, 25.0, 200.0, 0.0, NULL, NULL, NULL, NULL, NULL, 0.0, NULL, 'Moderate Risk', 0.2714, '["bp_stage1", "chol_borderline", "bmi_overweight"]', '[]', '2026-09-07 10:03:54.774687');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (9, 15, 5, 74.0, 1.0, 120, 80, 150.0, 27.32, 200.0, 1.0, NULL, NULL, NULL, NULL, NULL, 0.0, NULL, 'High Risk', 0.5857, '["fbs_flag_positive", "age_senior", "bp_stage1", "chol_borderline", "bmi_overweight"]', '[]', '2026-09-07 10:03:54.833706');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (10, 16, 6, 67.0, 0.0, 120, 80, 150.0, 27.32, 200.0, 1.0, NULL, NULL, NULL, NULL, NULL, 0.0, NULL, 'High Risk', 0.5857, '["fbs_flag_positive", "age_senior", "bp_stage1", "chol_borderline", "bmi_overweight"]', '[]', '2026-09-07 10:03:54.893630');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (11, 7, 2, 37.0, 1.0, 130, 85, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'Low Risk', 0.1143, '["BP_STAGE1", "AGE_YOUNG", "METABOLIC_BP_ELEVATED"]', '["Initiate or optimize antihypertensive therapy - target BP <130/80 mmHg.", "Consider ACE inhibitors/ARBs for patients with diabetes or CKD for renal protection.", "LOW RISK: Continue current healthy lifestyle and maintain regular health screenings.", "Reassess cardiovascular risk annually or sooner if symptoms develop."]', '2026-09-07 10:04:22.403532');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (12, 17, 2, 54.0, 1.0, 142, 90, 135.0, 29.0, 230.0, 1.0, NULL, NULL, NULL, 0.0, 0.0, 1.0, NULL, 'Critical Risk', 0.99, NULL, NULL, '2026-09-07 10:04:22.807012');
INSERT INTO patient_assessments (id, patient_id, doctor_id, age, sex, systolic_bp, diastolic_bp, max_heart_rate, bmi, cholesterol, fasting_blood_sugar, st_depression, chest_pain_type, exercise_angina, hypertension, diabetes, smoking, prior_medical_events, risk_level, risk_probability, triggered_rule_codes, clinical_recommendations, created_at) VALUES (13, 7, 3, 37.0, 1.0, 138, 88, 142.0, 26.8, 215.0, 0.0, 0.5, 2.0, 0.0, 1.0, 0.0, 0.0, NULL, 'High Risk', 0.5857, '["HYPERTENSION_DX", "BP_STAGE1", "CHOL_BORDERLINE", "ST_DEP_MILD", "CHEST_PAIN_NONANGINAL", "BMI_OVERWEIGHT", "HR_NORMAL", "AGE_YOUNG", "METABOLIC_BP_ELEVATED"]', '["Initiate or optimize antihypertensive therapy - target BP <130/80 mmHg.", "Consider ACE inhibitors/ARBs for patients with diabetes or CKD for renal protection.", "HIGH RISK: Schedule cardiology evaluation within 1-2 weeks for comprehensive workup.", "Aggressive risk factor modification required - medication adherence and lifestyle changes."]', '2026-09-07 10:04:22.953882');
SELECT setval(pg_get_serial_sequence('patient_assessments', 'id'), COALESCE((SELECT MAX(id) FROM patient_assessments), 1));

-- Data for audit_logs
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (1, 1, 'admin', 'created_doctor', 'User', 2, '{"name": "Dr. Sharma", "email": "dr.sharma@hospital.com", "specialization": "Cardiology"}', '2026-09-07 10:03:53.996205');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (2, 1, 'admin', 'created_doctor', 'User', 3, '{"name": "Dr. Mehta", "email": "dr.mehta@hospital.com", "specialization": "Internal Medicine"}', '2026-09-07 10:03:54.025793');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (3, 1, 'admin', 'created_doctor', 'User', 4, '{"name": "Dr. Khan", "email": "dr.khan@hospital.com", "specialization": "Endocrinology"}', '2026-09-07 10:03:54.060953');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (4, 1, 'admin', 'created_doctor', 'User', 5, '{"name": "Dr. Rao", "email": "dr.rao@hospital.com", "specialization": "Pulmonology"}', '2026-09-07 10:03:54.094295');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (5, 1, 'admin', 'created_doctor', 'User', 6, '{"name": "Dr. Iyer", "email": "dr.iyer@hospital.com", "specialization": "Nephrology"}', '2026-09-07 10:03:54.125872');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (6, 1, 'admin', 'created_patient', 'User', 7, '{"name": "Arjun", "email": "patient.arjun@hospital.com", "assigned_doctor": "Dr. Sharma", "age": 37, "sex": 1.0}', '2026-09-07 10:03:54.158391');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (7, 2, 'doctor', 'added_record', 'PatientAssessment', 1, '{"patient_name": "Arjun", "risk_level": "Moderate Risk", "risk_probability": 0.2714, "systolic_bp": 120, "diastolic_bp": 80.0}', '2026-09-07 10:03:54.198542');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (8, 1, 'admin', 'created_patient', 'User', 8, '{"name": "Riya", "email": "patient.riya@hospital.com", "assigned_doctor": "Dr. Mehta", "age": 68, "sex": 0.0}', '2026-09-07 10:03:54.240085');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (9, 3, 'doctor', 'added_record', 'PatientAssessment', 2, '{"patient_name": "Riya", "risk_level": "High Risk", "risk_probability": 0.4286, "systolic_bp": 120, "diastolic_bp": 80.0}', '2026-09-07 10:03:54.270330');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (10, 1, 'admin', 'created_patient', 'User', 9, '{"name": "Rohan", "email": "patient.rohan@hospital.com", "assigned_doctor": "Dr. Khan", "age": 46, "sex": 1.0}', '2026-09-07 10:03:54.468827');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (11, 4, 'doctor', 'added_record', 'PatientAssessment', 3, '{"patient_name": "Rohan", "risk_level": "High Risk", "risk_probability": 0.5857, "systolic_bp": 154.0, "diastolic_bp": 80.0}', '2026-09-07 10:03:54.495364');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (12, 1, 'admin', 'created_patient', 'User', 10, '{"name": "Ananya", "email": "patient.ananya@hospital.com", "assigned_doctor": "Dr. Rao", "age": 80, "sex": 0.0}', '2026-09-07 10:03:54.526425');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (13, 5, 'doctor', 'added_record', 'PatientAssessment', 4, '{"patient_name": "Ananya", "risk_level": "High Risk", "risk_probability": 0.5286, "systolic_bp": 120, "diastolic_bp": 80.0}', '2026-09-07 10:03:54.553857');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (14, 1, 'admin', 'created_patient', 'User', 11, '{"name": "Vikram", "email": "patient.vikram@hospital.com", "assigned_doctor": "Dr. Iyer", "age": 30, "sex": 1.0}', '2026-09-07 10:03:54.585328');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (15, 6, 'doctor', 'added_record', 'PatientAssessment', 5, '{"patient_name": "Vikram", "risk_level": "Moderate Risk", "risk_probability": 0.2714, "systolic_bp": 120, "diastolic_bp": 80.0}', '2026-09-07 10:03:54.613716');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (16, 1, 'admin', 'created_patient', 'User', 12, '{"name": "Pooja", "email": "patient.pooja@hospital.com", "assigned_doctor": "Dr. Sharma", "age": 51, "sex": 0.0}', '2026-09-07 10:03:54.644499');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (17, 2, 'doctor', 'added_record', 'PatientAssessment', 6, '{"patient_name": "Pooja", "risk_level": "Moderate Risk", "risk_probability": 0.3714, "systolic_bp": 120, "diastolic_bp": 80.0}', '2026-09-07 10:03:54.670836');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (18, 1, 'admin', 'created_patient', 'User', 13, '{"name": "Siddharth", "email": "patient.siddharth@hospital.com", "assigned_doctor": "Dr. Mehta", "age": 26, "sex": 1.0}', '2026-09-07 10:03:54.703555');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (19, 3, 'doctor', 'added_record', 'PatientAssessment', 7, '{"patient_name": "Siddharth", "risk_level": "Moderate Risk", "risk_probability": 0.3714, "systolic_bp": 120, "diastolic_bp": 80.0}', '2026-09-07 10:03:54.731613');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (20, 1, 'admin', 'created_patient', 'User', 14, '{"name": "Neha", "email": "patient.neha@hospital.com", "assigned_doctor": "Dr. Khan", "age": 20, "sex": 0.0}', '2026-09-07 10:03:54.764050');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (21, 4, 'doctor', 'added_record', 'PatientAssessment', 8, '{"patient_name": "Neha", "risk_level": "Moderate Risk", "risk_probability": 0.2714, "systolic_bp": 120, "diastolic_bp": 80.0}', '2026-09-07 10:03:54.791562');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (22, 1, 'admin', 'created_patient', 'User', 15, '{"name": "Aditya", "email": "patient.aditya@hospital.com", "assigned_doctor": "Dr. Rao", "age": 74, "sex": 1.0}', '2026-09-07 10:03:54.822470');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (23, 5, 'doctor', 'added_record', 'PatientAssessment', 9, '{"patient_name": "Aditya", "risk_level": "High Risk", "risk_probability": 0.5857, "systolic_bp": 120, "diastolic_bp": 80.0}', '2026-09-07 10:03:54.851425');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (24, 1, 'admin', 'created_patient', 'User', 16, '{"name": "Kavya", "email": "patient.kavya@hospital.com", "assigned_doctor": "Dr. Iyer", "age": 67, "sex": 0.0}', '2026-09-07 10:03:54.883719');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (25, 6, 'doctor', 'added_record', 'PatientAssessment', 10, '{"patient_name": "Kavya", "risk_level": "High Risk", "risk_probability": 0.5857, "systolic_bp": 120, "diastolic_bp": 80.0}', '2026-09-07 10:03:54.907990');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (26, 2, 'doctor', 'reassigned_patient', 'User', 7, '{"patient_id": 7, "patient_name": "Arjun", "old_doctor_id": 2, "old_doctor_name": "Dr. Sharma", "new_doctor_id": 3, "new_doctor_name": "Dr. Mehta", "reason": "Referred for comprehensive internal medicine evaluation"}', '2026-09-07 10:03:54.932796');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (27, 3, 'doctor', 'reassigned_patient', 'User', 8, '{"patient_id": 8, "patient_name": "Riya", "old_doctor_id": 3, "old_doctor_name": "Dr. Mehta", "new_doctor_id": 4, "new_doctor_name": "Dr. Khan", "reason": "Endocrinology consultation for diabetic glycaemic control"}', '2026-09-07 10:03:54.943646');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (28, 2, 'doctor', 'added_record', 'PatientAssessment', 11, '{"patient_id": 7, "patient_name": "Arjun", "assessment_id": 11, "risk_level": "Low Risk", "risk_probability": 0.1143, "systolic_bp": 130, "diastolic_bp": 85, "age": 37.0, "sex": 1.0}', '2026-09-07 10:04:22.418268');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (29, 2, 'doctor', 'reassigned_patient', 'User', 7, '{"patient_id": 7, "patient_name": "Arjun", "old_doctor_id": 2, "old_doctor_name": "Dr. Sharma", "new_doctor_id": 3, "new_doctor_name": "Dr. Mehta", "reason": "Specialized cardiology to internal medicine referral"}', '2026-09-07 10:04:22.613042');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (30, 3, 'doctor', 'recorded_diagnosis', 'DoctorDiagnosis', 11, '{"patient_id": 7, "patient_name": "Arjun", "doctor_id": 3, "doctor_name": "Dr. Mehta", "diagnosis_title": "Atherosclerotic Vascular Evaluation"}', '2026-09-07 10:04:22.692698');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (31, 2, 'doctor', 'guest_assessment', 'GuestEvaluation', NULL, '{"doctor_id": 2, "guest_name": "Walk-in Guest #101", "risk_level": "Critical Risk", "risk_probability": 0.99, "age": 54.0, "sex": 1.0}', '2026-09-07 10:04:22.761041');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (32, 18, 'patient', 'self_registered', 'User', 18, '{"patient_id": 18, "patient_name": "New Walkin Patient", "preferred_doctor_id": 2, "department": "Cardiology"}', '2026-09-07 10:04:22.844847');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (33, 2, 'doctor', 'forwarded_patient_request', 'PatientRegistrationRequest', 1, '{"request_id": 1, "from_doctor_id": 2, "to_doctor_id": 3, "to_doctor_name": "Dr. Mehta", "notes": "Needs Internal Medicine follow-up"}', '2026-09-07 10:04:22.870155');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (34, 3, 'doctor', 'accepted_patient_request', 'User', 18, '{"request_id": 1, "patient_id": 18, "patient_name": "New Walkin Patient", "doctor_id": 3, "doctor_name": "Dr. Mehta"}', '2026-09-07 10:04:22.882251');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (35, 2, 'doctor', 'requested_medicine', 'Medicine', 1, '{"medicine_id": 1, "medicine_name": "Metoprolol Succinate 50mg", "quantity": 100, "doctor_id": 2, "doctor_name": "Dr. Sharma"}', '2026-09-07 10:04:22.905398');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (36, 1, 'admin', 'procured_medicine', 'Medicine', 1, '{"medicine_id": 1, "medicine_name": "Metoprolol Succinate 50mg", "quantity_procured": 150, "allocated_to_doctor_id": 2, "allocated_to_doctor_name": "Dr. Sharma"}', '2026-09-07 10:04:22.919397');
INSERT INTO audit_logs (id, actor_user_id, actor_role, action, target_type, target_id, details, created_at) VALUES (37, 3, 'doctor', 'added_record', 'PatientAssessment', 13, '{"patient_id": 7, "patient_name": "Arjun", "assessment_id": 13, "risk_level": "High Risk", "risk_probability": 0.5857, "systolic_bp": 138, "diastolic_bp": 88, "age": 37.0, "sex": 1.0}', '2026-09-07 10:04:22.979825');
SELECT setval(pg_get_serial_sequence('audit_logs', 'id'), COALESCE((SELECT MAX(id) FROM audit_logs), 1));

-- Data for medicines
INSERT INTO medicines (id, name, generic_name, category, unit, quantity, requested_by_doctor_id, doctor_id, status, notes, requested_at, procured_at) VALUES (1, 'Metoprolol Succinate 50mg', 'Metoprolol', 'Beta-Blocker / Antihypertensive', 'tablet', 150, 2, 2, 'procured', 'For hypertension and angina management', '2026-09-07 10:04:22.894122', '2026-09-07 10:04:22.918587');
SELECT setval(pg_get_serial_sequence('medicines', 'id'), COALESCE((SELECT MAX(id) FROM medicines), 1));

-- Data for patient_registration_requests
INSERT INTO patient_registration_requests (id, patient_id, preferred_doctor_id, department_preference, status, notes, created_at, updated_at) VALUES (1, 18, 3, 'Cardiology', 'accepted', 'Accepted into clinical care roster by Dr. Dr. Mehta', '2026-09-07 10:04:22.847410', '2026-09-07 10:04:22.882959');
SELECT setval(pg_get_serial_sequence('patient_registration_requests', 'id'), COALESCE((SELECT MAX(id) FROM patient_registration_requests), 1));
