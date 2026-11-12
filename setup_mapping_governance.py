import sqlite3
from pathlib import Path

DB_PATH = Path(r"F:\khotiyan book\raipur_cadastre_voters.db")

SCHEMA_ADDITIONS = """
-- 1. Governance: Khatian & Voter Quarantine / Deduplication Policy Table
CREATE TABLE IF NOT EXISTS khatian_dedupe_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    has_blank_row BOOLEAN NOT NULL DEFAULT 0,
    disposition TEXT NOT NULL DEFAULT 'pending_review', -- 'pending_review', 'merge_blank', 'distinct_books'
    reviewed_at TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS voter_dedupe_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_no TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL,
    wards TEXT NOT NULL,
    names TEXT NOT NULL,
    disposition TEXT NOT NULL DEFAULT 'quarantine_duplicate_id', -- 'quarantine_duplicate_id', 'ec_ocr_error', 'verified_same_person'
    reviewed_at TIMESTAMP,
    notes TEXT
);

-- 2. Governance: Cross-Survey Dag Lineage & Mapping Table
-- Bridges historical CS / SA / RS parcel identifiers with modern BRS / Mutation
CREATE TABLE IF NOT EXISTS cross_survey_dag_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mouza TEXT NOT NULL,
    source_survey TEXT NOT NULL,     -- e.g. 'CS', 'SA', 'RS'
    source_dag_no TEXT NOT NULL,     -- former plot number
    target_survey TEXT NOT NULL,     -- e.g. 'BRS', 'Mutation'
    target_dag_no TEXT NOT NULL,     -- current/haal plot number
    relation_type TEXT NOT NULL,     -- '1_to_1', 'split', 'merge', 'part_of', 'unverified_coincidence'
    confidence_score REAL NOT NULL DEFAULT 0.5, -- 0.0 to 1.0
    verification_source TEXT,        -- 'milan_sheet_pdf', 'field_mutation_record', 'dag_number_coincidence'
    source_page TEXT,
    human_verified BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (mouza, source_survey, source_dag_no, target_survey, target_dag_no)
);

CREATE INDEX IF NOT EXISTS idx_lineage_source ON cross_survey_dag_lineage(mouza, source_survey, source_dag_no);
CREATE INDEX IF NOT EXISTS idx_lineage_target ON cross_survey_dag_lineage(mouza, target_survey, target_dag_no);
"""

def setup_governance():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript(SCHEMA_ADDITIONS)
    
    # Populate initial dedupe review for Khatians
    cur.execute("""
        INSERT OR IGNORE INTO khatian_dedupe_review (mouza, survey, khatian_no, row_count, has_blank_row, disposition)
        SELECT mouza, survey, khatian_no, COUNT(*) as cnt,
               MAX(CASE WHEN owners = '["—"]' THEN 1 ELSE 0 END) as has_blank,
               CASE WHEN MAX(CASE WHEN owners = '["—"]' THEN 1 ELSE 0 END) = 1 THEN 'merge_blank' ELSE 'pending_review' END
        FROM khatians
        GROUP BY mouza, survey, khatian_no
        HAVING cnt > 1;
    """)

    # Populate initial dedupe review for Voters
    cur.execute("""
        INSERT OR IGNORE INTO voter_dedupe_review (voter_no, occurrence_count, wards, names, disposition)
        SELECT voter_no, COUNT(*) as cnt, 
               GROUP_CONCAT(DISTINCT ward), 
               GROUP_CONCAT(name, ' | '),
               'quarantine_duplicate_id'
        FROM voters
        GROUP BY voter_no
        HAVING cnt > 1;
    """)

    con.commit()
    k_cnt = cur.execute("SELECT count(*) FROM khatian_dedupe_review").fetchone()[0]
    v_cnt = cur.execute("SELECT count(*) FROM voter_dedupe_review").fetchone()[0]
    print(f"Governance tables initialized successfully!")
    print(f"  • Khatian duplicate review groups: {k_cnt:,}")
    print(f"  • Voter duplicate review groups: {v_cnt:,}")
    con.close()

if __name__ == "__main__":
    setup_governance()

