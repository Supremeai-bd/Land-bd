import sqlite3
import json
import os
import time
import hashlib

DB_PATH = r"F:\khotiyan book\raipur_cadastre_voters.db"
KHATIANS_JSON = r"F:\khotiyan book\02_BACKUP_AND_RAW_DATA\Raipur_Land_Mapping_Data\raipur_master_khatians.json"
VOTERS_JSON = r"F:\khotiyan book\02_BACKUP_AND_RAW_DATA\Raipur_Land_Mapping_Data\raipur_all_voters.json"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

print("1. Creating SQLite schema with B-Tree indexes...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Khatians master table
cursor.execute("""
CREATE TABLE khatians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    owners TEXT NOT NULL,
    guardian TEXT,
    dags TEXT,
    total_land TEXT
);
""")

# Inverted dag-to-khatian map
cursor.execute("""
CREATE TABLE dag_khatian_map (
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    dag_no TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    PRIMARY KEY (mouza, survey, dag_no, khatian_no)
);
""")

# Voters table
cursor.execute("""
CREATE TABLE voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_no TEXT NOT NULL,
    name TEXT NOT NULL,
    father TEXT,
    mother TEXT,
    gender TEXT,
    ward TEXT NOT NULL,
    address TEXT
);
""")

# Users table
cursor.execute("""
CREATE TABLE users (
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
""")

# Saved khatians records
cursor.execute("""
CREATE TABLE saved_khatians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    dag_summary TEXT,
    owners_summary TEXT,
    notes TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
""")

# Saved voters records
cursor.execute("""
CREATE TABLE saved_voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    voter_no TEXT NOT NULL,
    name TEXT NOT NULL,
    father TEXT,
    mother TEXT,
    ward TEXT,
    address TEXT,
    relation_tag TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
""")

cursor.executemany("INSERT INTO khatians (mouza, survey, khatianNo, owners, guardian, dags, totalLand) VALUES (?, ?, ?, ?, ?, ?, ?)", [])
cursor.executemany("INSERT INTO dag_khatian_map (mouza, survey, dag_no, khatian_no) VALUES (?, ?, ?, ?)", list())
conn.commit()
print("2. Created tables: users, saved_khatians, saved_voters, khatians, dag_khatian_map, voters.")

# Seed users from existing master data? Placeholder - populate later from raipur_master_khatians.json etc.

conn.close()
