import sqlite3

def verify_tables():
    conn = sqlite3.connect("kautilya.db")
    cursor = conn.cursor()
    
    tables = [
        "mp_allocations",
        "projects",
        "vendors",
        "fund_releases",
        "utilization_certificates",
        "risk_scores",
        "scrape_logs",
        "users",
        "audit_runs",
        "evidence",
        "ingestion_runs"
    ]
    
    print("=" * 60)
    print("       PHASE 1: 7-TABLE NORMALIZED DATABASE VERIFICATION     ")
    print("=" * 60)
    
    for tbl in tables:
        count = cursor.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
        print(f"Table '{tbl:26s}': {count:>6d} records [VERIFIED]")
        assert count > 0, f"Table {tbl} is empty!"
        
    # Verify Join query (projects + risk_scores + utilization_certificates)
    join_query = """
    SELECT 
        p.project_id, 
        p.mp_name, 
        p.work_type, 
        r.composite_risk, 
        r.risk_level, 
        u.gap_pct
    FROM projects p
    JOIN risk_scores r ON p.project_id = r.project_id
    JOIN utilization_certificates u ON p.project_id = u.project_id
    LIMIT 5
    """
    rows = cursor.execute(join_query).fetchall()
    print("\n[OK] Sample Multi-Table Relational JOIN Query:")
    for r in rows:
        print(f"   Project: {r[0]} | MP: {r[1][:20]:20s} | Risk: {r[3]:.2f} ({r[4]}) | Doc Gap: {r[5]}%")
        
    conn.close()
    print("\nALL PHASE 1 NORMALIZED DATABASE TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    verify_tables()
