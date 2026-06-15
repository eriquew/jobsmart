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
-- ── USERS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    email           VARCHAR(100)    DEFAULT NULL,
    location        VARCHAR(100)    DEFAULT NULL,
    profile_yaml    LONGTEXT        DEFAULT NULL,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── JOB SCORES PER USER ────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_scores (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    job_id                  INT             NOT NULL,
    user_id                 INT             NOT NULL,
    score_total             FLOAT           DEFAULT 0,
    score_technical         FLOAT           DEFAULT 0,
    score_seniority         FLOAT           DEFAULT 0,
    score_industry          FLOAT           DEFAULT 0,
    score_location          FLOAT           DEFAULT 0,
    flag_french_required    TINYINT(1)      DEFAULT 0,
    extracted_skills        TEXT            DEFAULT NULL,
    scored_at               DATETIME        DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_job_user  (job_id, user_id),
    INDEX idx_user_score        (user_id, score_total),
    INDEX idx_job_id            (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── JOB TRACKING PER USER ──────────────────────────────────
CREATE TABLE IF NOT EXISTS job_tracking (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    job_id      INT             NOT NULL,
    user_id     INT             NOT NULL,
    status      ENUM(
                    'new',
                    'reviewed',
                    'applied',
                    'interview',
                    'rejected'
                )               DEFAULT 'new',
    notes       TEXT            DEFAULT NULL,
    updated_at  DATETIME        DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_job_user_track    (job_id, user_id),
    INDEX idx_user_status               (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

