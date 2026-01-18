-- MediScribe Database Setup
-- Run this in MySQL Workbench
drop database mediscribe_db;
-- Create database
CREATE DATABASE IF NOT EXISTS mediscribe_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mediscribe_db;

-- Prescription table
CREATE TABLE IF NOT EXISTS prescription (
    id INT AUTO_INCREMENT PRIMARY KEY,
    unique_id VARCHAR(36) UNIQUE NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    raw_text TEXT,
    urdu_text TEXT,
    audio_path VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
select * from prescription;
-- Medication table
CREATE TABLE IF NOT EXISTS medication (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prescription_id INT NOT NULL,
    name VARCHAR(200) NOT NULL,
    dose VARCHAR(100),
    schedule VARCHAR(200),
    confidence VARCHAR(20),
    FOREIGN KEY (prescription_id) REFERENCES prescription(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX idx_prescription_status ON prescription(status);
CREATE INDEX idx_prescription_created ON prescription(created_at);
CREATE INDEX idx_medication_prescription ON medication(prescription_id);

