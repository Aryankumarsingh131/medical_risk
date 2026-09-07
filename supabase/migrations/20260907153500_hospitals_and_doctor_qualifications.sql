-- Delta migration: Add hospitals, hospital_doctor_availability, and update doctor qualifications

ALTER TABLE users ADD COLUMN IF NOT EXISTS degree VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS years_of_experience INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS certifications TEXT;

CREATE TABLE IF NOT EXISTS hospitals (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    address VARCHAR(300) NOT NULL,
    contact_number VARCHAR(30) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    available_beds INTEGER DEFAULT 0,
    icu_beds_available INTEGER DEFAULT 0,
    ventilators_available INTEGER DEFAULT 0,
    blood_bank_available BOOLEAN DEFAULT FALSE,
    emergency_services_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hospital_doctor_availability (
    id SERIAL PRIMARY KEY,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,
    specialization VARCHAR(100) NOT NULL,
    available_doctors INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Update doctor qualifications
UPDATE users SET degree = 'MBBS, MD (Cardiology), FACC', years_of_experience = 14, certifications = 'Board Certified Cardiologist, ACLS Certified, Fellow of the American College of Cardiology' WHERE id = 2;
UPDATE users SET degree = 'MBBS, MD (General Medicine)', years_of_experience = 11, certifications = 'Board Certified Internal Physician, Advanced Diabetes Specialist' WHERE id = 3;
UPDATE users SET degree = 'MBBS, MD, DM (Endocrinology)', years_of_experience = 9, certifications = 'Endocrine Society Fellow, Certified Thyroid & Metabolic Specialist' WHERE id = 4;
UPDATE users SET degree = 'MBBS, DNB (Respiratory Medicine)', years_of_experience = 12, certifications = 'FCCCP, Critical Care Pulmonologist' WHERE id = 5;
UPDATE users SET degree = 'MBBS, MD, DM (Nephrology)', years_of_experience = 15, certifications = 'Renal Transplant Specialist, Dialysis Director Certification' WHERE id = 6;

-- Insert hospitals and availability
INSERT INTO hospitals (id, name, address, contact_number, latitude, longitude, available_beds, icu_beds_available, ventilators_available, blood_bank_available, emergency_services_available) VALUES (1, 'City Care Super Specialty Hospital', '123 Healthcare Ave, Medical District, Mumbai', '+91 98765 00100', 19.076, 72.8777, 42, 12, 6, TRUE, TRUE) ON CONFLICT (id) DO NOTHING;
INSERT INTO hospitals (id, name, address, contact_number, latitude, longitude, available_beds, icu_beds_available, ventilators_available, blood_bank_available, emergency_services_available) VALUES (2, 'Apollo Heart & Emergency Institute', '45 Park Road, South City, Mumbai', '+91 98765 00200', 19.12, 72.85, 18, 8, 4, TRUE, TRUE) ON CONFLICT (id) DO NOTHING;
INSERT INTO hospitals (id, name, address, contact_number, latitude, longitude, available_beds, icu_beds_available, ventilators_available, blood_bank_available, emergency_services_available) VALUES (3, 'Metro Critical Care Hospital', '88 Station Road, North District, Mumbai', '+91 98765 00300', 19.01, 72.83, 15, 3, 2, FALSE, TRUE) ON CONFLICT (id) DO NOTHING;
INSERT INTO hospital_doctor_availability (id, hospital_id, specialization, available_doctors) VALUES (1, 1, 'Cardiology', 4) ON CONFLICT (id) DO NOTHING;
INSERT INTO hospital_doctor_availability (id, hospital_id, specialization, available_doctors) VALUES (2, 1, 'Internal Medicine', 6) ON CONFLICT (id) DO NOTHING;
INSERT INTO hospital_doctor_availability (id, hospital_id, specialization, available_doctors) VALUES (3, 1, 'Pulmonology', 2) ON CONFLICT (id) DO NOTHING;
INSERT INTO hospital_doctor_availability (id, hospital_id, specialization, available_doctors) VALUES (4, 2, 'Cardiology', 5) ON CONFLICT (id) DO NOTHING;
INSERT INTO hospital_doctor_availability (id, hospital_id, specialization, available_doctors) VALUES (5, 2, 'Endocrinology', 3) ON CONFLICT (id) DO NOTHING;
INSERT INTO hospital_doctor_availability (id, hospital_id, specialization, available_doctors) VALUES (6, 3, 'Nephrology', 2) ON CONFLICT (id) DO NOTHING;
INSERT INTO hospital_doctor_availability (id, hospital_id, specialization, available_doctors) VALUES (7, 3, 'Internal Medicine', 4) ON CONFLICT (id) DO NOTHING;
SELECT setval(pg_get_serial_sequence('hospitals', 'id'), COALESCE((SELECT MAX(id) FROM hospitals), 1));
SELECT setval(pg_get_serial_sequence('hospital_doctor_availability', 'id'), COALESCE((SELECT MAX(id) FROM hospital_doctor_availability), 1));