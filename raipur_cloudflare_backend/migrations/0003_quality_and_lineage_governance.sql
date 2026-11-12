-- Migration 0003: Data Quality, Deduplication Governance & Cross-Survey Dag Lineage

-- 1. Governance: Khatian & Voter Quarantine / Deduplication Policy Table
CREATE TABLE IF NOT EXISTS khatian_dedupe_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    has_blank_row BOOLEAN NOT NULL DEFAULT 0,
    disposition TEXT NOT NULL DEFAULT 'pending_review',
    reviewed_at TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS voter_dedupe_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_no TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL,
    wards TEXT NOT NULL,
    names TEXT NOT NULL,
    disposition TEXT NOT NULL DEFAULT 'quarantine_duplicate_id',
    reviewed_at TIMESTAMP,
    notes TEXT
);

-- 2. Governance: Cross-Survey Dag Lineage & Mapping Table
-- Bridges historical CS / SA / RS parcel identifiers with modern BRS / Mutation
CREATE TABLE IF NOT EXISTS cross_survey_dag_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mouza TEXT NOT NULL,
    source_survey TEXT NOT NULL,
    source_dag_no TEXT NOT NULL,
    target_survey TEXT NOT NULL,
    target_dag_no TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    confidence_score REAL NOT NULL DEFAULT 0.5,
    verification_source TEXT,
    source_page TEXT,
    human_verified BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (mouza, source_survey, source_dag_no, target_survey, target_dag_no)
);

CREATE INDEX IF NOT EXISTS idx_lineage_source ON cross_survey_dag_lineage(mouza, source_survey, source_dag_no);
CREATE INDEX IF NOT EXISTS idx_lineage_target ON cross_survey_dag_lineage(mouza, target_survey, target_dag_no);
