#!/usr/bin/env python3

import random
from collections import defaultdict
import math

TEAMS = {
    "ari":"Cardinals",
    "atl":"Falcons",
    "bal":"Ravens",
    "buf":"Bills",
    "car":"Panthers",
    "chi":"Bears",
    "cin":"Bengals",
    "cle":"Browns",
    "dal":"Cowboys",
    "den":"Broncos",
    "det":"Lions",
    "gb":"Packers",
    "hou":"Texans",
    "ind":"Colts",
    "jax":"Jaguars",
    "kc":"Chiefs",
    "lac":"Chargers",
    "lar":"Rams",
    "lv":"Raiders",
    "mia":"Dolphins",
    "mn":"Vikings",
    "ne":"Patriots",
    "no":"Saints",
    "nyg":"Giants",
    "nyj":"Jets",
    "phi":"Eagles",
    "pit":"Steelers",
    "sea":"Seahawks",
    "sf":"49ers",
    "tb":"Buccaneers",
    "ten":"Titans",
    "was":"Commanders"
}


def use_Error():
    """Prints a help message showing all valid team abbreviations."""
    print("Not a valid name try:")
    for key in TEAMS:
        print(key, sep=" ", end=" ")
    print("")

def normalize_input(user_input):
    """
    Normalizes user input to handle common shortcuts and variations
    for 'yes'/'no', 'favorite'/'underdog', and 'quit'.
    """
    if not user_input:
        return user_input
    
    user_input = user_input.lower().strip()
    
    shortcuts = {
        'f': 'favorite',
        'fav': 'favorite', 
        'u': 'underdog',
        'und': 'underdog',
        'dog': 'underdog',
        'y': 'yes',
        'n': 'no',
        'q': 'quit',
        'neither': 'neither' 
    }
    
    return shortcuts.get(user_input, user_input)

def get_team_input(prompt):
    """
    Gets and validates team input from the user.
    Handles abbreviations, full names, and 'quit'.
    """
    while True:
        try:
            team = input(prompt).strip()
            if not team:
                print("Please enter a team abbreviation or 'q' to quit.")
                continue
            
            normalized = normalize_input(team)
            if normalized == 'quit':
                return 'QUIT'
                

            if normalized in TEAMS:
                return TEAMS[normalized]
            
            for abbr, full_name in TEAMS.items():
                if team.lower() == full_name.lower():
                    return full_name
            
            print(f"'{team}' is not a valid team. Valid abbreviations:")
            use_Error()
            
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return 'QUIT' 
        except Exception as e:
            print(f"Error: {e}")
            continue

def weighted(spread):
    """
    Returns the favorite's win probability based on a positive spread.
    This model is based on historical NFL data mapping spreads to win rates.
    """
    if 16.5 <= spread:
        weight_F = 0.93
    elif 13.5 <= spread < 16.5:
        weight_F = 0.91
    elif 10.5 <= spread < 13.5:
        weight_F = 0.87
    elif 9 <= spread < 10.5:
        weight_F = 0.83
    elif 7.5 <= spread < 9:
        weight_F = 0.79
    elif 6.5 <= spread < 7.5:
        weight_F = 0.75
    elif 5.5 <= spread < 6.5:
        weight_F = 0.71
    elif 4.5 <= spread < 5.5:
        weight_F = 0.68
    elif 3.5 <= spread < 4.5:
        weight_F = 0.65
    elif 2.5 <= spread < 3.5:
        weight_F = 0.60
    elif 1.5 <= spread < 2.5:
        weight_F = 0.56
    elif 0.5 <= spread < 1.5:
        weight_F = 0.53
    else:
        weight_F = 0.50
    return weight_F

def generate_slates_ga(games, num_slates=5, population_size=500, generations=300, mutation_rate=0.07, underdog_bonus=0.45):
    """
    Generates optimized slates of picks using a Genetic Algorithm.
    [TUNING: underdog_bonus default changed from .05 to 0.45 for N=15 pool]
    """
    if not games:
        return []

    game_probs = []
    for game in games:
        adjusted_spread = game['spread'] 
        initial_favorite = game['favorite']
        initial_underdog = game['underdog']

        if adjusted_spread >= 0:
            fav_prob = weighted(adjusted_spread)
            dog_prob = 1 - fav_prob
        else:
            dog_prob = weighted(abs(adjusted_spread)) 
            fav_prob = 1 - dog_prob

        game_probs.append({
            'favorite': {'team': initial_favorite, 'prob': fav_prob},
            'underdog': {'team': initial_underdog, 'prob': dog_prob}
        })

    def calculate_fitness(individual):
        """Calculates the fitness of a single slate (individual)."""
        overall_prob = 1.0
        underdog_count = 0
        for i, pick in enumerate(individual):
            if pick == game_probs[i]['favorite']['team']:
                overall_prob *= game_probs[i]['favorite']['prob']
            else:
                overall_prob *= game_probs[i]['underdog']['prob']
                underdog_count += 1

        fitness = overall_prob * (1 + underdog_bonus * underdog_count)
        return fitness, overall_prob, underdog_count

    def create_individual():
        """Creates one random individual, weighted by probability."""
        picks = []
        for prob_info in game_probs:
            pick = random.choices(
                [prob_info['favorite']['team'], prob_info['underdog']['team']],
                weights=[prob_info['favorite']['prob'], prob_info['underdog']['prob']]
            )[0]
            picks.append(pick)
        return picks

    # --- GA Execution ---
    
    # 1. Initialization
    population = [create_individual() for _ in range(population_size)]

    for _ in range(generations):
        # 2. Evaluation
        pop_with_fitness = [(ind, calculate_fitness(ind)) for ind in population]
        
        # 3. Selection (Elitism: keep top 50%)
        pop_with_fitness.sort(key=lambda x: x[1][0], reverse=True)
        parent_pool = [ind for ind, fit in pop_with_fitness[:population_size // 2]]
        
        # 4. Crossover & Mutation
        offspring = []
        while len(offspring) < population_size:
            parent1, parent2 = random.choices(parent_pool, k=2)
            
            # Single-point crossover
            if len(games) < 2:
                child = parent1[:] # Avoid mutation by reference
            else:
                split_point = random.randint(1, len(games) - 1)
                child = parent1[:split_point] + parent2[split_point:]
            
            # Mutation
            for i in range(len(child)):
                if random.random() < mutation_rate:
                    # Flip the pick
                    child[i] = game_probs[i]['underdog']['team'] if child[i] == game_probs[i]['favorite']['team'] else game_probs[i]['favorite']['team']
            
            offspring.append(child)
        population = offspring # New generation replaces the old

    # Get final, unique slates from the last generation
    final_population_details = []
    unique_slates = set()
    for ind in population:
        fitness, overall_prob, underdog_count = calculate_fitness(ind)
        slate_tuple = tuple(ind)
        if slate_tuple not in unique_slates:
            final_population_details.append({
                'picks': ind,
                'fitness': fitness,
                'overall_prob': overall_prob,
                'underdog_count': underdog_count
            })
            unique_slates.add(slate_tuple)
    
    # Return the best N slates, sorted by fitness
    final_population_details.sort(key=lambda x: x['fitness'], reverse=True)
    return final_population_details[:num_slates]


def get_game():
    """
    Gathers all data for a single game from the user.
    Calculates all adjustments and returns a final 'adjusted_spread'.
    Returns a tuple: (favorite, underdog, raw_spread, adjusted_spread, pick)
    [REVISION: 'pick' is now returned as None, as the GA should make the final pick.]
    """
    print("Type 'q' or 'quit' at any time to return to main menu.")
    
    favorite = get_team_input("What team is the favorite? ")
    if favorite is None or favorite == 'QUIT':
        return None
    
    while True:
        underdog = get_team_input("What team is the underdog? ")
        if underdog is None or underdog == 'QUIT':
            return None
        if underdog != favorite:
            break
        else:
            print("Underdog cannot be the same as the favorite. Please choose a different team.")
    
    while True:
        try:
            spread_input = input("What is the spread? (or 'q' to quit): ").strip()
            
            if normalize_input(spread_input) in ['quit', 'q']:
                return None
            
            if not spread_input:
                print("Please enter a valid spread or 'q' to quit.")
                continue
            spread = float(spread_input) 
            if spread < 0:
                print("Spread should be positive (favorite is expected to win by this many points).")
                continue
            break
        except ValueError:
            print("Invalid number for spread. Please enter a decimal (e.g., 3.5) or 'q' to quit.")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return None
    
    adjusted_spread = spread

    while True:
        home_team_input = input("Which team is home? (Enter 'f' for favorite, 'u' for underdog, 'q' to quit): ").strip()
        home_team = normalize_input(home_team_input)
        
        if home_team in ['quit', 'q']:
            return None
        
        if home_team in ['favorite', 'underdog']:
            break
        elif home_team_input.lower() in ['f', 'fav']:
            home_team = 'favorite'
            break
        elif home_team_input.lower() in ['u', 'und', 'dog']:
            home_team = 'underdog'
            break
        else:
            print("Please enter 'f' for favorite, 'u' for underdog, or 'q' to quit.")

    
    if home_team == "underdog":
        adjusted_spread -= 0.5
    
    while True:
        prime_time_input = input("Is this a prime time game Thursday, Sunday, or Monday night? (y/n/q): ").strip()
        prime_time = normalize_input(prime_time_input)
        
        if prime_time in ['quit', 'q']:
            return None
        
        if prime_time in ['yes', 'no']:
            break
        elif prime_time_input.lower() in ['y', 'n']:
            prime_time = 'yes' if prime_time_input.lower() == 'y' else 'no'
            break
        else:
            print("Please enter 'y' for yes, 'n' for no, or 'q' to quit.")
    
    if prime_time == 'yes':
        if home_team == "favorite":
            adjusted_spread += 0.5
        elif home_team == "underdog":
            adjusted_spread -= 1.0 
    

    adjusted_spread = adjust_for_rest(adjusted_spread)
    if adjusted_spread is None: return None 
    

    adjusted_spread = adjust_for_momentum(favorite, underdog, adjusted_spread)
    if adjusted_spread is None: return None 
    

    if is_division_game(favorite, underdog):
        print("-> Division game detected - applying 0.85x modifier.")
        adjusted_spread = adjusted_spread * 0.85
    
    print(f"\nOriginal spread: {spread:.1f}")
    print(f"Final Adjusted spread: {adjusted_spread:.1f}")
    
    pick = None
    
    return(favorite, underdog, spread, adjusted_spread, pick)

def score(points):
    """
    Selects a weighted random score for the tiebreaker.
    'points' is the O/U total for the tiebreaker game.
    
    This function weights two things:
    1. Closeness to the O/U (distance_weight)
    2. Preference for common NFL totals (position_weight, nums array)
    """
    nums = [41, 37, 51, 44, 40, 43, 47, 33, 48, 30, 34, 55, 45]
    total = float(points)
    
    weights = []
    
    for i, num in enumerate(nums):
        # Weight 1: How close is this number to the O/U?
        # (1.0 / (1.0 + distance))
        distance_weight = 1.0 / (1.0 + abs(num - total))
        
        # Weight 2: Give a slight bias to numbers earlier in the list
        # (This is a weak prior for more common totals)
        position_weight = (len(nums) - i) / len(nums) 
        
        combined_weight = distance_weight * position_weight
        weights.append(combined_weight)
    
    # Normalize weights and make a random choice
    total_weight = sum(weights)
    
    if total_weight == 0 or math.isnan(total_weight):
        return random.choice(nums)
        
    normalized_weights = [w / total_weight for w in weights]
    
    selected_total = random.choices(nums, weights=normalized_weights)[0]
    
    return selected_total

def is_division_game(favorite_full, underdog_full):
    """Checks if two teams are in the same division."""
    favorite_abbr = None
    underdog_abbr = None
    
    for abbr, name in TEAMS.items():
        if name == favorite_full:
            favorite_abbr = abbr
        if name == underdog_full:
            underdog_abbr = abbr
    
    if not favorite_abbr or not underdog_abbr:
        return False 
    
    divisions = {
        'AFC_EAST': ['buf', 'mia', 'ne', 'nyj'],
        'AFC_NORTH': ['bal', 'cin', 'cle', 'pit'],
        'AFC_SOUTH': ['hou', 'ind', 'jax', 'ten'],
        'AFC_WEST': ['den', 'kc', 'lac', 'lv'],
        'NFC_EAST': ['dal', 'nyg', 'phi', 'was'],
        'NFC_NORTH': ['chi', 'det', 'gb', 'mn'],
        'NFC_SOUTH': ['atl', 'car', 'no', 'tb'],
        'NFC_WEST': ['ari', 'lar', 'sea', 'sf']
    }
    
    for division in divisions.values():
        if favorite_abbr in division and underdog_abbr in division:
            return True
    
    return False

def adjust_for_momentum(favorite, underdog, spread):
    """Adjusts spread based on 3+ game winning streaks."""
    while True:
        fav_input = input(f"Is {favorite} on a 3+ game win streak? (y/n/q): ").strip()
        fav_streak = normalize_input(fav_input)
        if fav_streak == 'quit': return None
        
        if fav_streak in ['yes', 'no']:
            break
        elif fav_input.lower() in ['y', 'n']:
            fav_streak = 'yes' if fav_input.lower() == 'y' else 'no'
            break
        else:
            print("Please enter 'y' or 'n'.")
    
    while True:
        dog_input = input(f"Is {underdog} on a 3+ game win streak? (y/n/q): ").strip()
        dog_streak = normalize_input(dog_input)
        if dog_streak == 'quit': return None
        
        if dog_streak in ['yes', 'no']:
            break
        elif dog_input.lower() in ['y', 'n']:
            dog_streak = 'yes' if dog_input.lower() == 'y' else 'no'
            break
        else:
            print("Please enter 'y' or 'n'.")
    
    adjustment = 0
    if fav_streak == 'yes':
        adjustment += 1.0 
        print("-> Momentum adjustment: +1.0 (fav streak)")
    if dog_streak == 'yes':
        adjustment -= 1.0 
        print("-> Momentum adjustment: -1.0 (dog streak)")
        
    return spread + adjustment

def adjust_for_rest(spread):
    """Adjusts spread for significant rest advantage (e.g., bye week vs. short week)."""
    while True:
        rest_input = input("Rest advantage? ('f' fav, 'u' dog, 'n' neither, 'q' quit): ").strip()
        rest_advantage = normalize_input(rest_input)
        if rest_advantage == 'quit': return None
        
        if rest_advantage in ['favorite', 'underdog', 'neither']:
            break
        # Allow shortcuts
        elif rest_input.lower() in ['f', 'fav', 'u', 'und', 'dog', 'n']:
            if rest_input.lower() in ['f', 'fav']:
                rest_advantage = 'favorite'
            elif rest_input.lower() in ['u', 'und', 'dog']:
                rest_advantage = 'underdog'
            else:
                rest_advantage = 'neither'
            break
        else:
            print("Please enter: 'f', 'u', 'n', or 'q'.")
    
    if rest_advantage == "favorite":
        print("-> Rest adjustment: +1.0 (fav advantage)")
        return spread + 1.0
    elif rest_advantage == "underdog":
        print("-> Rest adjustment: -1.5 (dog advantage)")
        return spread - 1.5
    
    return spread 