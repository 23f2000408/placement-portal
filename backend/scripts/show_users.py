import sqlite3, json, sys
DB = r'C:\Users\srini\.copilot\repos\copilot-worktrees\placementportal\srinithi0104-supreme-meme\placement-portal\backend\placement.db'
try:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, email, role, is_active, created_at FROM 'user'")
    rows = cur.fetchall()
    print(json.dumps(rows, default=str))
except Exception as e:
    print('ERROR:', e, file=sys.stderr)
    sys.exit(1)
