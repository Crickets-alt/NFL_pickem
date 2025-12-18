import sqlite3
from datetime import datetime

def connect_db(db_name="picks.db"):
    """Connect to the database, ensure schema is up-to-date, and return connection and cursor."""
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row 
    cur = conn.cursor()


    cur.execute("""
                CREATE TABLE IF NOT EXISTS picks (
                id INTEGER PRIMARY KEY,
                date TEXT,
                week INTEGER,
                year INTEGER,
                favorite TEXT,
                underdog TEXT,
                spread REAL,
                adjusted_spread REAL,
                pick TEXT,
                winner TEXT,
                correct INTEGER
                )
                """)
    
    cur.execute("""
                CREATE TABLE IF NOT EXISTS weekly_scores (
                id INTEGER PRIMARY KEY,
                week INTEGER,
                year INTEGER,
                score INTEGER
                )
                """)
    cur.execute("""
                CREATE TABLE IF NOT EXISTS non_winners (
                id INTEGER PRIMARY KEY,
                week INTEGER,
                year INTEGER,
                team TEXT,
                result TEXT
                )
                """)

    cur.execute("PRAGMA table_info(picks)")
    columns = [row['name'] for row in cur.fetchall()]
    
    if 'year' not in columns:
        print("Adding 'year' column to the database...")
        cur.execute("ALTER TABLE picks ADD COLUMN year INTEGER")
        conn.commit()
        print("Column added.")

    
    if 'adjusted_spread' not in columns:
        print("Adding 'adjusted_spread' column to the database...")
        cur.execute("ALTER TABLE picks ADD COLUMN adjusted_spread REAL")
        cur.execute("UPDATE picks SET adjusted_spread = spread WHERE adjusted_spread IS NULL")
        conn.commit()
        print("Column added and backfilled.")


    cur.execute("""
                UPDATE picks 
                SET year = CAST(strftime('%Y', date) AS INTEGER) 
                WHERE year IS NULL
                """)
    conn.commit()

    cur.execute("""
                CREATE TABLE IF NOT EXISTS adjustment_tracking (
                id INTEGER PRIMARY KEY,
                pick_id INTEGER,
                adjustment_type TEXT,
                original_spread REAL,
                adjusted_spread REAL,
                was_correct INTEGER,
                FOREIGN KEY (pick_id) REFERENCES picks (id)
                )
                """)

    cur.execute("""
                CREATE TABLE IF NOT EXISTS generated_slates (
                id INTEGER PRIMARY KEY,
                week INTEGER,
                year INTEGER,
                method TEXT,
                fitness REAL,
                overall_prob REAL,
                underdog_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
    
    cur.execute("""
                CREATE TABLE IF NOT EXISTS slate_picks (
                id INTEGER PRIMARY KEY,
                slate_id INTEGER,
                pick_order INTEGER,
                team_pick TEXT,
                favorite TEXT,
                underdog TEXT,
                spread REAL,
                FOREIGN KEY (slate_id) REFERENCES generated_slates (id) ON DELETE CASCADE
                )
                """)
    
    conn.commit()
    return conn, cur

def view_picks(conn, cur, filters=None):
    """View picks with optional filters"""
    
    base_query = "SELECT id, date, week, year, favorite, underdog, spread, adjusted_spread, pick, winner, correct FROM picks"
    params = []
    where_clauses = []
    
    if filters:
        if 'week' in filters:
            where_clauses.append("week = ?")
            params.append(filters['week'])
        
        if 'year' in filters:
            where_clauses.append("year = ?")
            params.append(filters['year'])
            
        if 'correct' in filters:
            where_clauses.append("correct = ?")
            params.append(filters['correct'])
            
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
    
    cur.execute(base_query, params)
    rows = cur.fetchall()

    if not rows:
        print("No picks found matching your criteria.")
        return

    print("\n{:<5} {:<12} {:<6} {:<6} {:<15} {:<15} {:<8} {:<12} {:<15} {:<15} {:<8}".format(
        "ID", "Date", "Week", "Year", "Favorite", "Underdog", "Spread", "Adj Spread", "Pick", "Winner", "Correct"))
    print("-" * 130)

    count = 0
    wins = 0
    for row in rows:
        count += 1
        if row['correct'] == 1:
            wins += 1

        pick_str = row['pick'] if row['pick'] is not None else "N/A"
        spread_str = f"{row['spread']:.1f}" if row['spread'] is not None else "N/A"
        adj_spread_str = f"{row['adjusted_spread']:.1f}" if row['adjusted_spread'] is not None else "N/A"
        winner_str = row['winner'] if row['winner'] is not None else "N/A"
        correct_str = "Yes" if row['correct'] == 1 else "No" if row['correct'] == 0 else "N/A"

        print("{:<5} {:<12} {:<6} {:<6} {:<15} {:<15} {:<8} {:<12} {:<15} {:<15} {:<8}".format(
            row['id'], row['date'], row['week'], row['year'], row['favorite'], row['underdog'], 
            spread_str, adj_spread_str, pick_str, winner_str, correct_str))
    
    print("\nTotal picks: {}".format(count))
    if count > 0:
        print("Correct picks: {} ({:.1f}%)".format(wins, (wins/count)*100))

def update_pick(conn, cur, pick_id):
    """Update an existing pick using column names for safety."""
    cur.execute("SELECT * FROM picks WHERE id = ?", (pick_id,))
    pick = cur.fetchone()
    
    if not pick:
        print(f"No pick found with ID {pick_id}")
        return
    
    print("\nCurrent pick details:")
    print(f"ID: {pick['id']}")
    print(f"Date: {pick['date']}")
    print(f"Week: {pick['week']}")
    print(f"Year: {pick['year']}")
    print(f"Favorite: {pick['favorite']}")
    print(f"Underdog: {pick['underdog']}")
    print(f"Spread: {pick['spread']}")
    print(f"Adjusted Spread: {pick['adjusted_spread']}")
    print(f"Pick: {pick['pick'] or 'Not set'}")
    print(f"Winner: {pick['winner'] or 'Not set'}")
    print(f"Correct: {pick['correct'] if pick['correct'] is not None else 'Not set'}")
    
    print("\nWhat would you like to update?")
    print("1. Week")
    print("2. Favorite")
    print("3. Underdog")
    print("4. Spread")
    print("5. Pick")
    print("6. Winner")
    print("7. Cancel")
    
    choice = input("\nEnter your choice (1-7): ")
    
    if choice == "6":
        new_winner = input("Enter winner (favorite/underdog): ").lower()
        if new_winner not in ["favorite", "underdog"]:
            print("Winner must be 'favorite' or 'underdog'")
            return
        
        winner = pick['favorite'] if new_winner == "favorite" else pick['underdog']
        cur.execute("UPDATE picks SET winner = ? WHERE id = ?", (winner, pick_id))
        
        correct = 1 if winner == pick['pick'] else 0
        cur.execute("UPDATE picks SET correct = ? WHERE id = ?", (correct, pick_id))
    
    elif choice == "7":
        print("Update cancelled.")
        return
        
    else:
        print("Update logic for other fields is not fully implemented in this example.")
        return

    conn.commit()
    print("Pick updated successfully")

def delete_pick(conn, cur, pick_id):
    """Delete a pick by ID"""
    cur.execute("SELECT * FROM picks WHERE id = ?", (pick_id,))
    pick = cur.fetchone()
    
    if not pick:
        print(f"No pick found with ID {pick_id}")
        return
    
    print("\nYou are about to delete this pick:")
    print(f"ID: {pick['id']}")
    print(f"Date: {pick['date']}")
    print(f"Week: {pick['week']}")
    print(f"Favorite: {pick['favorite']}")
    print(f"Underdog: {pick['underdog']}")
    print(f"Spread: {pick['spread']}")
    print(f"Pick: {pick['pick'] or 'N/A'}")
    
    confirm = input("\nAre you sure you want to delete this pick? (y/n): ").lower()
    
    if confirm == 'y':
        cur.execute("DELETE FROM picks WHERE id = ?", (pick_id,))
        cur.execute("DELETE FROM slate_picks WHERE favorite = ? AND underdog = ? AND slate_id IN (SELECT id FROM generated_slates WHERE week = ? AND year = ?)", 
                    (pick['favorite'], pick['underdog'], pick['week'], pick['year']))
        conn.commit()
        print("Pick deleted successfully from 'picks' and any associated 'slate_picks'.")
    else:
        print("Deletion cancelled")

def backup_database(conn, db_name="picks.db"):
    """Create a backup of the database"""
    conn.close()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}_{db_name}"
    
    try:
        with open(db_name, 'rb') as source:
            with open(backup_name, 'wb') as dest:
                dest.write(source.read())
        print(f"Database backed up successfully to {backup_name}")
    except Exception as e:
        print(f"Backup failed: {e}")
    
    return connect_db(db_name)

def analyze_performance(cur):
    """Analyze pick performance by NFL season (not calendar year)"""
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) FROM picks WHERE correct IS NOT NULL")
    result = cur.fetchone()
    total = result[0]
    wins = result[1] if result[1] is not None else 0
    
    if total == 0:
        print("No completed picks found")
        return
    
    win_pct = (wins / total) * 100 if total > 0 else 0
    
    print("\n===== PERFORMANCE ANALYSIS =====")
    print(f"Overall record: {wins}-{total-wins} ({win_pct:.1f}%)")
    
    print("\nPerformance by spread range (based on raw spread):")
    spread_ranges = [(0, 3.5), (3.5, 6.5), (6.5, 9.5), (9.5, 100)]
    
    for low, high in spread_ranges:
        cur.execute("""
            SELECT COUNT(*), SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END)
            FROM picks
            WHERE spread >= ? AND spread < ? AND correct IS NOT NULL
        """, (low, high))
        
        range_result = cur.fetchone()
        range_total = range_result[0]
        range_wins = range_result[1] if range_result[1] is not None else 0

        if range_total > 0:
            range_pct = (range_wins / range_total) * 100
            print(f"Spread {low}-{high}: {range_wins}-{range_total-range_wins} ({range_pct:.1f}%)")
    
    print("\nPerformance by NFL season:")
    cur.execute("""
        SELECT 
            CASE 
                WHEN strftime('%m', date) >= '09'
                THEN strftime('%Y', date)
                ELSE (strftime('%Y', date) - 1)
            END as season,
            COUNT(*), 
            SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END)
        FROM picks
        WHERE correct IS NOT NULL AND date IS NOT NULL
        GROUP BY season
        ORDER BY season DESC
    """)
    
    for row in cur.fetchall():
        season = row['season']
        season_total = row[1]
        season_wins = row[2] if row[2] is not None else 0
        
        season_pct = (season_wins / season_total) * 100
        print(f"{season} Season: {season_wins}-{season_total-season_wins} ({season_pct:.1f}%)")
    
    print("\nPerformance by week:")
    cur.execute("""
        SELECT 
            week,
            COUNT(*), 
            SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END)
        FROM picks
        WHERE correct IS NOT NULL
        GROUP BY week
        ORDER BY week
    """)
    
    for row in cur.fetchall():
        week = row['week']
        week_total = row[1]
        week_wins = row[2] if row[2] is not None else 0
        week_pct = (week_wins / week_total) * 100
        print(f"Week {week}: {week_wins}-{week_total-week_wins} ({week_pct:.1f}%)")
    
    print("\nPerformance by pick type:")
    cur.execute("""
        SELECT 
            CASE 
                WHEN pick = favorite THEN 'Favorite'
                WHEN pick = underdog THEN 'Underdog'
                ELSE 'Unknown'
            END as pick_type,
            COUNT(*), 
            SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END)
        FROM picks
        WHERE correct IS NOT NULL AND pick IS NOT NULL
        GROUP BY pick_type
        ORDER BY pick_type
    """)
    
    for row in cur.fetchall():
        pick_type = row['pick_type']
        type_total = row[1]
        type_wins = row[2] if row[2] is not None else 0
        
        type_pct = (type_wins / type_total) * 100
        print(f"{pick_type}: {type_wins}-{type_total-type_wins} ({type_pct:.1f}%)")

def clean_database(conn, cur):
    """View and clean up problematic database entries"""
    print("\n===== DATABASE CLEANUP =====")
    
    cur.execute("""
                SELECT id, week, favorite, underdog, spread, pick
                FROM picks
                ORDER BY id ASC
                """)
    rows = cur.fetchall()
    
    if not rows:
        print("No picks found in database.")
        return
    
    print("\nCurrent picks in database:")
    print("{:<5} {:<6} {:<15} {:<15} {:<8} {:<15}".format(
        "ID", "Week", "Favorite", "Underdog", "Spread", "Pick"))
    print("-" * 70)
    

    for row in rows:
        pick_str = row['pick'] if row['pick'] is not None else "N/A"
        spread_str = f"{row['spread']:.1f}" if row['spread'] is not None else "N/A"
        
        print("{:<5} {:<6} {:<15} {:<15} {:<8} {:<15}".format(
            row['id'], 
            row['week'], 
            row['favorite'], 
            row['underdog'], 
            spread_str, 
            pick_str
        ))
    
    delete_ids = input("\nEnter IDs to delete (comma-separated) or 'all' to clear all: ")
    
    if delete_ids.lower() == 'all':
        confirm = input("Are you sure you want to delete ALL picks? This cannot be undone. (y/n): ")
        if confirm.lower() == 'y':
            cur.execute("DELETE FROM picks")
            cur.execute("DELETE FROM generated_slates") 
            cur.execute("DELETE FROM slate_picks") 
            conn.commit()
            print("All picks and generated slates have been deleted.")
    elif delete_ids:
        try:
            ids_to_delete = [int(id.strip()) for id in delete_ids.split(',')]
            
            for pick_id in ids_to_delete:
                cur.execute("SELECT week, year, favorite, underdog FROM picks WHERE id = ?", (pick_id,))
                pick = cur.fetchone()
                if pick:
                    cur.execute("DELETE FROM picks WHERE id = ?", (pick_id,))
                    cur.execute("""
                        DELETE FROM slate_picks 
                        WHERE favorite = ? AND underdog = ? 
                        AND slate_id IN (SELECT id FROM generated_slates WHERE week = ? AND year = ?)
                        """, (pick['favorite'], pick['underdog'], pick['week'], pick['year']))
                
            conn.commit()
            print(f"Deleted {len(ids_to_delete)} entries from 'picks' and cleaned associated 'slate_picks'.")
            
            cur.execute("""
                DELETE FROM generated_slates 
                WHERE id NOT IN (SELECT DISTINCT slate_id FROM slate_picks)
            """)
            conn.commit()
            print("Cleaned up any slates that are now empty.")

        except ValueError:
            print("Invalid input. Please enter comma-separated numbers.")

def main():
    """Main function to run the database commands"""
    db_name = input("Enter database name (default: picks.db): ") or "picks.db"
    conn, cur = connect_db(db_name)
    
    while True:
        print("\n===== NFL PICKS DATABASE MANAGER =====")
        print("1. View picks")
        print("2. Update a pick")
        print("3. Delete a pick")
        print("4. Backup database")
        print("5. Analyze performance")
        print("6. Clean database")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ")
        
        if choice == "1":
            filters = {}
            filter_by = input("Filter by week? (y/n): ").lower()
            if filter_by == 'y':
                week = input("Enter week number: ")
                if week.isdigit():
                    filters['week'] = int(week)
            
            filter_by = input("Filter by year? (y/n): ").lower()
            if filter_by == 'y':
                year = input("Enter year (YYYY): ")
                if len(year) == 4 and year.isdigit():
                    filters['year'] = int(year)
            
            filter_by = input("Show only correct picks? (y/n): ").lower()
            if filter_by == 'y':
                filters['correct'] = 1
            
            view_picks(conn, cur, filters)
        
        elif choice == "2":
            pick_id = input("Enter the ID of the pick to update: ")
            if pick_id.isdigit():
                update_pick(conn, cur, int(pick_id))
            else:
                print("ID must be a number")
        
        elif choice == "3":
            pick_id = input("Enter the ID of the pick to delete: ")
            if pick_id.isdigit():
                delete_pick(conn, cur, int(pick_id))
            else:
                print("ID must be a number")
        
        elif choice == "4":
            conn, cur = backup_database(conn, db_name)
        
        elif choice == "5":
            analyze_performance(cur)
        
        elif choice == "6":
            clean_database(conn, cur)
        
        elif choice == "7":
            print("Exiting...")
            break
        
        else:
            print("Invalid choice. Please try again.")
    
    conn.close()

if __name__ == "__main__":
    main()