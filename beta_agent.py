import sqlite3
import datetime
import json
from alpha_agent import alpha_agent, AgentState
from database import DB_NAME

def beta_agent(state: AgentState) -> dict:
    report = state["report"]
    report_status = report.status
    report_subject = report.subject.lower().strip()
    
    if report_status == "UNVERIFIED":
        return {
            "beta_action": "Discard (Unverified)",
            "trace": ["Beta discarded unverified claim early to protect database integrity."]
        }

    action = "Discard" 
    conn = sqlite3.connect(DB_NAME)
    
    try:
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM claims WHERE subject = ?""", (report_subject,))
        results = cursor.fetchall()
        
        current_time = datetime.datetime.now().isoformat()
        sources_json = json.dumps(report.sources)
        
        if results and len(results) > 0:
            existing_status = results[0][3]  
            existing_summary = results[0][5] 
            
            if existing_status == report_status or existing_status == "FLAGGED":
                action = "Discard (Redundant)"
            else:
                action = "Flag (Pending Review)"
                appended_summary = f"{existing_summary}\n\n[CONFLICT DETECTED {current_time}]: Challenger claim '{report.claim}' returned {report_status}. Reason: {report.summary}"
                
                existing_sources = json.loads(results[0][6])
                merged_sources = list(set(existing_sources + report.sources))
                merged_sources_json = json.dumps(merged_sources)
                
                cursor.execute("""
                    UPDATE claims 
                    SET verification_status = 'FLAGGED', summary = ?, sources = ?, timestamp = ? 
                    WHERE subject = ?
                """, (appended_summary, merged_sources_json, current_time, report_subject))
                conn.commit()
                
        else:
            try:
                if report_status == "VERIFIED":
                    action = "Insert"
                    cursor.execute("""INSERT INTO claims (subject, claim_text, verification_status, confidence, summary, sources, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                   (report_subject, report.claim, "VERIFIED", report.confidence, report.summary, sources_json, current_time)) 
                    conn.commit() 
                    
                elif report_status == "FALSE":
                    action = "Insert (Debunked)"
                    cursor.execute("""INSERT INTO claims (subject, claim_text, verification_status, confidence, summary, sources, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                   (report_subject, report.claim, "FALSE", report.confidence, report.summary, sources_json, current_time)) 
                    conn.commit()
            except sqlite3.IntegrityError:
                action = "Discard (Concurrent Duplicate Detected)"
                
    finally:
        conn.close()

    beta_log = f"Beta checked the database and executed action: {action}."
    return {
        "beta_action": action,
        "trace": [beta_log]
    }