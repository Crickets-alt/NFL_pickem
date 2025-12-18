import db_commands
from nflpick import *
from datetime import datetime


def handle_new_game(cur, conn, week, year, teams_picked):
    print("\nEnter the information for a new pick:")
    game_data = get_game() 
    if game_data:
        
        (favorite, underdog, raw_spread, adjusted_spread, pick) = game_data
        if favorite not in teams_picked and underdog not in teams_picked:
            
            cur.execute("""
                INSERT INTO picks (date, week, year, favorite, underdog, spread, adjusted_spread, pick)
                VALUES (date('now', 'localtime'), ?, ?, ?, ?, ?, ?, ?)
            """, (week, year, favorite, underdog, raw_spread, adjusted_spread, pick))
            conn.commit()
            print(f"\nGame Added: {favorite} vs. {underdog}")
            return (favorite, underdog, pick)
        else:
            print("\nOne of these teams has already been picked this week.")
    return None

def handle_advanced_ga(cur, conn, week, year):
    """Generates, displays, saves, and allows selection of slates via Genetic Algorithm."""
    print(f"\nClearing previously generated slates for Week {week}, {year}...")
    cur.execute("""
        DELETE FROM slate_picks 
        WHERE slate_id IN (SELECT id FROM generated_slates WHERE week = ? AND year = ?)
    """, (week, year))
    rows_deleted = cur.execute("DELETE FROM generated_slates WHERE week = ? AND year = ?", (week, year)).rowcount
    conn.commit()
    if rows_deleted > 0:
        print(f"Cleared {rows_deleted} old slate(s).")
    else:
        print("No previous slates found to clear.")

    print("\nGenerating optimized slates with Genetic Algorithm...")
    
    cur.execute("SELECT favorite, underdog, adjusted_spread as spread FROM picks WHERE week = ? AND year = ?", (week, year))
    games_for_slate = [dict(row) for row in cur.fetchall()]
    
    if not games_for_slate:
        print(f"No games entered for Week {week}. Please add games using 'N'.")
        return None

    top_slates = generate_slates_ga(games_for_slate, num_slates=5)

    if not top_slates:
        print("Could not generate slates.")
        return None

    print("Saving generated slates to the database...")
    for slate in top_slates:
        cur.execute("""
            INSERT INTO generated_slates (week, year, method, fitness, overall_prob, underdog_count)
            VALUES (?, ?, 'GA', ?, ?, ?)
        """, (week, year, slate['fitness'], slate['overall_prob'], slate['underdog_count']))
        slate_id = cur.lastrowid
        
        slate_picks_with_context = []
        temp_games = list(games_for_slate)
        for pick in slate['picks']:
            for game in temp_games:
                if pick in (game['favorite'], game['underdog']):
                    slate_picks_with_context.append({
                        'team_pick': pick,
                        'favorite': game['favorite'],
                        'underdog': game['underdog'],
                        'spread': game['spread'] 
                    })
                    temp_games.remove(game)
                    break
        
        for i, pick_data in enumerate(slate_picks_with_context):
            cur.execute("""
                INSERT INTO slate_picks (slate_id, pick_order, team_pick, favorite, underdog, spread)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (slate_id, i + 1, pick_data['team_pick'], pick_data['favorite'], pick_data['underdog'], pick_data['spread']))
    conn.commit()
    print("Slates saved successfully.")
    
    
    handle_view_slates(cur, week, year, limit=5)

    while True:
        try:
            selection = input(f"\nWhich slate do you want to set as your final picks for Week {week}? (1-5 or 'c' to cancel): ").strip().lower()
            if selection == 'c': break
            selection_idx = int(selection) - 1
            if 0 <= selection_idx < len(top_slates):
                final_picks = top_slates[selection_idx]['picks']
                print(f"\nSlate #{selection_idx + 1} selected as your final picks!")
                for game in games_for_slate:
                    chosen_winner = next((p for p in final_picks if p in (game['favorite'], game['underdog'])), None)
                    if chosen_winner:
                        cur.execute("""
                            UPDATE picks SET pick = ? WHERE week = ? AND year = ? AND favorite = ? AND underdog = ?
                        """, (chosen_winner, week, year, game['favorite'], game['underdog']))
                conn.commit()
                print("Database has been updated with your final picks.")
                return final_picks
            else:
                print("Invalid selection.")
        except ValueError:
            print("Please enter a valid number.")
    return None

def handle_view_slates(cur, week, year, limit=None):
    """Queries and displays previously generated slates from the database."""
    print("\n--- Viewing Saved Slates ---")
    query = "SELECT * FROM generated_slates WHERE week = ? AND year = ? ORDER BY fitness DESC"
    params = (week, year)
    if limit:
        query += " LIMIT ?"
        params += (limit,)

    slates = cur.execute(query, params).fetchall()

    if not slates:
        print(f"No saved slates found for Week {week}, {year}.")
        return

    for i, slate in enumerate(slates, 1):
        prob_percent = slate['overall_prob'] * 100
        print(f"\n--- Slate #{i} (DB ID: {slate['id']}) --- (Fitness: {slate['fitness']:.4f})")
        print(f"Risk Profile:      {slate['underdog_count']} Underdog(s)")
        print(f"Success Chance:    {prob_percent:.4f}%")
        print("-" * 55)
        
        picks = cur.execute("SELECT * FROM slate_picks WHERE slate_id = ? ORDER BY pick_order", (slate['id'],)).fetchall()
        for j, pick in enumerate(picks, 1):
            status = "Favorite" if pick['team_pick'] == pick['favorite'] else "Underdog"
            spread_str = f"-{pick['spread']}" if status == "Favorite" else f"+{pick['spread']}"
            print(f"{j:>2}. {pick['team_pick']:<20} ({status} {spread_str})")
    print("\n" + "="*55)

def handle_print_picks(cur, week, year, winners, non_winner, over_under):
    """Prints the final selected picks for the week and saves to a file if requested."""

    
    output_lines = []
    output_lines.append("\n" + "="*40)
    output_lines.append(f"NFL PICKS - WEEK {week}".center(40))
    output_lines.append("="*40 + "\n")
    
    if over_under is not None:
        output_lines.append("TIEBREAKER SCORE".center(40))
        output_lines.append(f"{over_under} total points".center(40))
        output_lines.append("-"*40 + "\n")
    
    if non_winner is not None:
        output_lines.append("NON-WINNER PICK".center(40))
        output_lines.append(f"{non_winner}".center(40))
        output_lines.append("-"*40 + "\n")
    
    output_lines.append("TEAM SELECTIONS".center(40))
    if winners:
        for i, team in enumerate(winners, 1):
            output_lines.append(f"{i:>2}. {team.center(31)}")
    else:
        output_lines.append("No teams selected yet".center(40))
    
    output_lines.append("\n" + "="*40)
    
    final_output_str = "\n".join(output_lines)
    print(final_output_str)
    
    if input("\nDo you want to save this to a file? (y/n): ").lower() == 'y':
        filename = f"week_{week}_picks.txt"
        with open(filename, 'w') as f:
            f.write(f"NFL PICKS - WEEK {week}\n\n")
            if over_under is not None:
                f.write(f"Tiebreaker Score: {over_under} total points\n\n")
            if non_winner is not None:
                f.write(f"Non-Winner Pick: {non_winner}\n\n")
            f.write("Team Selections:\n")
            for i, team in enumerate(winners, 1):
                f.write(f"{i:>2}. {team}\n")
        print(f"Picks saved to {filename}")

def main():
    conn, cur = db_commands.connect_db("picks.db")

    while True:
        week_input = input("What week will the games be? (or 'q' to quit) ")
        if week_input.lower() == 'q':
            exit()
        if week_input.isdigit() and 1 <= int(week_input) <= 30:
            week = int(week_input)
            break
        else:
            print("Invalid week number.")

    current_year = datetime.now().year
    
    existing_picks = cur.execute("SELECT favorite, underdog, pick FROM picks WHERE week = ? AND year = ?", (week, current_year)).fetchall()
    teams_picked = [team for row in existing_picks for team in (row['favorite'], row['underdog'])]
    winners = [row['pick'] for row in existing_picks if row['pick']]
    

    non_winner_row = cur.execute("SELECT team FROM non_winners WHERE week = ? AND year = ?", (week, current_year)).fetchone()
    non_winner = non_winner_row['team'] if non_winner_row else None
    
    over_under_row = cur.execute("SELECT score FROM weekly_scores WHERE week = ? AND year = ?", (week, current_year)).fetchone()
    over_under = over_under_row['score'] if over_under_row else None

    while True:
        games_picked_so_far = len(teams_picked) // 2
        print(f"\n--- Week {week} | Year {current_year} | Games Entered: {games_picked_so_far} ---")
        
        choice_input = input(
            "New Game (N), Update (U), Score (S), Loser (L), Print (P), Advanced GA (A), View Slates (V), or Quit (Q)? "
        ).strip().upper()

        if choice_input == "N":
            result = handle_new_game(cur, conn, week, current_year, teams_picked)
            if result:
                fav, und, pick = result
                teams_picked.extend([fav, und])
                if pick not in winners:
                    winners.append(pick)
        
        elif choice_input == "A":
            new_picks = handle_advanced_ga(cur, conn, week, current_year)
            if new_picks:
                winners = new_picks

        elif choice_input == "V":
            handle_view_slates(cur, week, current_year)

        elif choice_input == "P":
            if not winners:
                winners = [row['pick'] for row in cur.execute("SELECT pick FROM picks WHERE week = ? AND year = ?", (week, current_year)).fetchall() if row['pick']]
            
            if not winners:
                 print("\nNo final picks selected. Please generate slates with 'A' and make a selection first.")
            else:
                handle_print_picks(cur, week, current_year, winners, non_winner, over_under)

        elif choice_input == "Q":
            break

        elif choice_input =="U":
            cur.execute("SELECT id FROM picks WHERE winner IS NULL OR correct IS NULL")
            rows = cur.fetchall()
            missing = [row['id'] for row in rows]
            if rows:
                print("\nThe following games have missing information:")
                for game_id in missing:
                    cur.execute("SELECT date, week, favorite, underdog FROM picks WHERE id = ?", (game_id,))
                    result = cur.fetchone()
                    print(f"ID# {game_id}: {result['date']} Wk {result['week']} - {result['favorite']} vs {result['underdog']}")
                    
                while True:
                    id_input = input("\nEnter the id of the game you want to update (or 'q' to go back): ")
                    if id_input.lower() == 'q':
                        break
                    if id_input.isdigit() and int(id_input) in missing:
                        id_to_update = int(id_input)
                        cur.execute("SELECT favorite, underdog, pick FROM picks WHERE id = ?", (id_to_update,))
                        row = cur.fetchone()
                        
                        print(f"\nUpdating Game ID {id_to_update}: {row['favorite']} vs {row['underdog']} (Your pick: {row['pick']})")
                        
                       
                        winner_for_db = None
                        correct = 0
                        
                        while True: 
                            result_input = input("Enter the winning team's abbreviation, or 'TIE' for a tie: ").strip().upper()

                            if result_input == 'TIE':
                                winner_for_db = 'TIE'
                                correct = 0 
                                break
                            
                           
                            team_name = TEAMS.get(result_input.lower()) 
                            
                            if not team_name: 
                                for abbr, full_name in TEAMS.items():
                                    if result_input == full_name.upper():
                                        team_name = full_name
                                        break
                            
                            if team_name and team_name in (row['favorite'], row['underdog']):
                                winner_for_db = team_name
                                correct = 1 if winner_for_db == row['pick'] else 0
                                break
                            else:
                                print(f"Invalid input. Please enter an abbreviation for '{row['favorite']}', '{row['underdog']}', or 'TIE'.")
                        
                        
                        cur.execute("UPDATE picks SET winner = ?, correct = ? WHERE id = ?", (winner_for_db, correct, id_to_update))
                        conn.commit()
                        print(f"Updated game {id_to_update}. Result: {winner_for_db}")
                        break
                        
                    else:
                        print("Enter a valid integer ID from the list above or 'q' to go back")
            else:
                print("\nAll games have complete information.")

        elif choice_input == "S":
            print("Type 'q' or 'quit' at any time to return to main menu.")
            while True:
                try:
                    points_input = input("What is the over/under for the game? (or 'q' to quit): ").strip()
                    if normalize_input(points_input) in ['quit', 'q']:
                        print("Returning to main menu.")
                        break
                    points = float(points_input)
                    if points <= 0:
                        print("Over/under should be a positive number.")
                        continue
                    total = score(points)
                    cur.execute("INSERT OR REPLACE INTO weekly_scores (week, year, score) VALUES (?, ?, ?)", (week, current_year, total))
                    conn.commit()
                    print(f"Predicted total score: {total}")
                    
                    over_under = total
                    break
                except (ValueError, TypeError):
                    print("Invalid number. Please enter a decimal number (e.g., 45.5) or 'q' to quit.")

        elif choice_input == "L":
            cur.execute("SELECT favorite, underdog, spread, pick FROM picks WHERE week = ? AND year = ?", (week, current_year))
            games_this_week = cur.fetchall()
            
            if not games_this_week:
                print(f"\nNo games found for Week {week}, {current_year}.")
                continue

            available_teams = []
            for game in games_this_week:
                if game['pick'] == game['favorite']:
                    available_teams.append({'team': game['underdog'], 'spread': f"+{game['spread']}", 'sort_spread': game['spread']})
                else:
                    available_teams.append({'team': game['favorite'], 'spread': f"-{game['spread']}", 'sort_spread': -game['spread']})

            available_teams.sort(key=lambda x: x['sort_spread'], reverse=True)

            print(f"\nAvailable teams for non-winner pick (Week {week}, {current_year}):")
            print("-" * 40)
            
            for i, team_info in enumerate(available_teams, 1):
                print(f"{i:2d}. {team_info['team']:<20} ({team_info['spread']:>5})")
            
            while True:
                non_winner_input = input("\nEnter your non-winner pick (team abbreviation) or 'q' to quit: ").strip()
                if normalize_input(non_winner_input) in ['quit', 'q']:
                    break
                
                valid_team_name = None
                if non_winner_input in TEAMS:
                    valid_team_name = TEAMS[non_winner_input]
                else:
                    for abbr, full_name in TEAMS.items():
                        if non_winner_input.lower() == full_name.lower():
                            valid_team_name = full_name
                            break
                
                if valid_team_name and any(d['team'] == valid_team_name for d in available_teams):
                    cur.execute("INSERT OR REPLACE INTO non_winners (week, year, team, result) VALUES (?, ?, ?, NULL)", (week, current_year, valid_team_name))
                    conn.commit()
                    print(f"\n{valid_team_name} has been selected as your non-winner for Week {week}.")
                   
                    non_winner = valid_team_name
                    break
                else:
                    print(f"'{non_winner_input}' is not a valid or available team. Please choose from the list.")

        
        else:
            print("Invalid option. Please try again.")

    conn.close()

if __name__ == "__main__":
    main()