import os
import json
import time

def reconcile():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(base_dir, "02_BACKUP_AND_RAW_DATA", "Raipur_Land_Mapping_Data")
    khatians_path = os.path.join(raw_dir, "raipur_master_khatians.json")
    target_dag_index_path = os.path.join(raw_dir, "raipur_master_dag_index.json")
    mouza_manifest_path = os.path.join(raw_dir, "mouza_manifest.json")
    voters_path = os.path.join(raw_dir, "raipur_all_voters.json")
    exceptions_path = os.path.join(base_dir, ".work", "verification", "voter_duplicates_exception.json")

    os.makedirs(os.path.join(base_dir, ".work", "verification"), exist_ok=True)

    print("1. Loading raw master khatians...")
    start_t = time.time()
    with open(khatians_path, "r", encoding="utf-8") as f:
        khatians = json.load(f)
    print(f"   Loaded {len(khatians):,} khatian records in {time.time()-start_t:.2f}s")

    # 1. Reconcile Dag Index
    print("2. Re-generating bidirectional 100% synchronized Dag Index...")
    dag_index = {}
    relation_count = 0

    for r in khatians:
        mouza = str(r.get("mouza") or "").strip()
        survey = str(r.get("survey") or "").strip()
        khatian_no = str(r.get("khatianNo") or "").strip()
        dags = r.get("dags") or []
        if isinstance(dags, (int, str)):
            dags = [str(dags)]

        if mouza not in dag_index:
            dag_index[mouza] = {}
        if survey not in dag_index[mouza]:
            dag_index[mouza][survey] = {}

        for dag in dags:
            dag_str = str(dag).strip()
            if not dag_str:
                continue
            if dag_str not in dag_index[mouza][survey]:
                dag_index[mouza][survey][dag_str] = []
            if khatian_no not in dag_index[mouza][survey][dag_str]:
                dag_index[mouza][survey][dag_str].append(khatian_no)
                relation_count += 1

    print(f"   Built inverted dag index with {relation_count:,} relations across {len(dag_index)} mouzas.")

    # Write back raipur_master_dag_index.json
    with open(target_dag_index_path, "w", encoding="utf-8") as f:
        json.dump(dag_index, f, ensure_ascii=False, indent=2)
    print(f"   Saved updated {target_dag_index_path}")

    # 2. Normalize Mouza Manifest
    print("3. Harmonizing mouza manifest with actual raw dataset mouzas...")
    raw_mouzas = sorted(list(set(str(r.get("mouza") or "").strip() for r in khatians if str(r.get("mouza") or "").strip())))
    mouza_manifest_dict = {m: {"index": idx + 1} for idx, m in enumerate(raw_mouzas)}
    with open(mouza_manifest_path, "w", encoding="utf-8") as f:
        json.dump(mouza_manifest_dict, f, ensure_ascii=False, indent=2)
    print(f"   Saved {len(mouza_manifest_dict)} canonical mouzas in {mouza_manifest_path}")

    # 3. Analyze and export duplicate voter exceptions
    if os.path.exists(voters_path):
        print("4. Analyzing duplicate voter IDs and exporting exception file...")
        with open(voters_path, "r", encoding="utf-8") as f:
            voters = json.load(f)

        voter_map = {}
        for idx, v in enumerate(voters):
            v_no = str(v.get("voterNo") or "").strip()
            if not v_no:
                continue
            if v_no not in voter_map:
                voter_map[v_no] = []
            voter_map[v_no].append({
                "record_index": idx,
                "name": v.get("name"),
                "father": v.get("father"),
                "mother": v.get("mother"),
                "gender": v.get("gender"),
                "ward": v.get("ward"),
                "address": v.get("address"),
                "sourcePdf": v.get("sourcePdf")
            })

        duplicates = {k: v for k, v in voter_map.items() if len(v) > 1}
        print(f"   Found {len(duplicates):,} duplicate voter IDs across {sum(len(v) for v in duplicates.values()):,} records.")

        with open(exceptions_path, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total_duplicate_ids": len(duplicates),
                "total_duplicate_records": sum(len(v) for v in duplicates.values()),
                "exceptions": duplicates
            }, f, ensure_ascii=False, indent=2)
        print(f"   Exported duplicate voter audit file to {exceptions_path}")

    print("\n✅ Reconciliation complete in {:.2f}s!".format(time.time() - start_t))

if __name__ == "__main__":
    reconcile()
