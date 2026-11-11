-- 0002: Align D1 with the Worker contract and add exact lookup indexes.
-- Existing saved rows are preserved. Legacy integer ids are cast to text.
-- Voter numbers are intentionally not UNIQUE: the source contains reviewed duplicates.

CREATE TABLE saved_khatians_v2 (
    id TEXT PRIMARY KEY,
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
INSERT INTO saved_khatians_v2 (id,user_id,mouza,survey,khatian_no,dag_summary,owners_summary,notes,saved_at)
SELECT CAST(id AS TEXT),user_id,mouza,survey,khatian_no,dag_summary,owners_summary,notes,saved_at
FROM saved_khatians;
DROP TABLE saved_khatians;
ALTER TABLE saved_khatians_v2 RENAME TO saved_khatians;

CREATE TABLE saved_voters_v2 (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    voter_no TEXT NOT NULL,
    name TEXT NOT NULL,
    father TEXT,
    mother TEXT,
    ward TEXT,
    address TEXT,
    relation_tag TEXT,
    notes TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
INSERT INTO saved_voters_v2 (id,user_id,voter_no,name,father,mother,ward,address,relation_tag,notes,saved_at)
SELECT CAST(id AS TEXT),user_id,voter_no,name,father,mother,ward,address,relation_tag,'',saved_at
FROM saved_voters;
DROP TABLE saved_voters;
ALTER TABLE saved_voters_v2 RENAME TO saved_voters;

ALTER TABLE voters ADD COLUMN source_pdf TEXT;
CREATE INDEX IF NOT EXISTS idx_voters_voter_no ON voters(voter_no);
CREATE INDEX IF NOT EXISTS idx_khatians_khatian_no ON khatians(khatian_no);
CREATE INDEX IF NOT EXISTS idx_dag_exact_lookup ON dag_khatian_map(dag_no,mouza,survey);
CREATE INDEX IF NOT EXISTS idx_saved_khatians_user ON saved_khatians(user_id,saved_at);
CREATE INDEX IF NOT EXISTS idx_saved_voters_user ON saved_voters(user_id,saved_at);
