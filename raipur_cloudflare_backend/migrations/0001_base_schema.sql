-- 0001: Baseline schema. IF NOT EXISTS permits adoption of the existing D1
-- database; 0002 then migrates the two saved-record tables to the Worker contract.
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    phone TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'citizen',
    status TEXT NOT NULL DEFAULT 'pending',
    association_license_no TEXT,
    password_hash TEXT NOT NULL,
    approved_by TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS khatians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    owners TEXT NOT NULL,
    guardian TEXT,
    dags TEXT,
    total_land TEXT
);
CREATE TABLE IF NOT EXISTS dag_khatian_map (
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    dag_no TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    PRIMARY KEY (mouza,survey,dag_no,khatian_no)
);
CREATE TABLE IF NOT EXISTS voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_no TEXT NOT NULL,
    name TEXT NOT NULL,
    father TEXT,
    mother TEXT,
    gender TEXT,
    ward TEXT NOT NULL,
    address TEXT
);
CREATE TABLE IF NOT EXISTS saved_khatians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    dag_summary TEXT,
    owners_summary TEXT,
    notes TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS saved_voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    voter_no TEXT NOT NULL,
    name TEXT NOT NULL,
    father TEXT,
    mother TEXT,
    ward TEXT,
    address TEXT,
    relation_tag TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_khatians_lookup ON khatians(mouza,survey,khatian_no);
CREATE INDEX IF NOT EXISTS idx_dag_lookup ON dag_khatian_map(mouza,survey,dag_no);
CREATE INDEX IF NOT EXISTS idx_voters_name ON voters(name);
CREATE INDEX IF NOT EXISTS idx_voters_father ON voters(father);
