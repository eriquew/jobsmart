-- JobSmart Database Schema
-- MySQL 8.0
-- Run with: mysql -u root -p jobsmart < model/database/schema.sql

USE jobsmart;

CREATE TABLE IF NOT EXISTS jobs (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    source              VARCHAR(50)     NOT NULL,
    title               VARCHAR(255)    NOT NULL,
    company             VARCHAR(255),
    location            VARCHAR(255),
    salary_min          INT             DEFAULT NULL,
    salary_max          INT             DEFAULT NULL,
    currency            VARCHAR(10)     DEFAULT 'CAD',
    description         LONGTEXT,
    url                 VARCHAR(1000),
    date_posted         DATE            DEFAULT NULL,
    date_ingested       DATETIME        DEFAULT CURRENT_TIMESTAMP,

    -- Scoring fields
    score_total         FLOAT           DEFAULT 0,
    score_technical     FLOAT           DEFAULT 0,
    score_seniority     FLOAT           DEFAULT 0,
    score_industry      FLOAT           DEFAULT 0,
    score_location      FLOAT           DEFAULT 0,

    -- Flags
    flag_french_required TINYINT(1)     DEFAULT 0,
    extracted_skills    TEXT            DEFAULT NULL,

    -- Application tracking
    status              ENUM(
                            'new',
                            'reviewed',
                            'applied',
                            'interview',
                            'rejected'
                        )               DEFAULT 'new',

    -- Deduplication key
    dedup_hash          VARCHAR(64)     UNIQUE,

    -- Indexes
    INDEX idx_score     (score_total),
    INDEX idx_status    (status),
    INDEX idx_source    (source),
    INDEX idx_date      (date_ingested),
    INDEX idx_location  (location)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;