NFL Pick'em & Genetic Algorithm Optimizer

A Python-based command-line interface (CLI) tool designed to manage NFL pick'em pools. This application allows users to manually track games, apply algorithmic adjustments (momentum, rest, division rivalries), and utilizes a Genetic Algorithm (GA) to generate optimized pick slates based on historical win probabilities.

Quick Start

Run the main program:

'''
python3 nfl_main.py
'''

Main Menu Commands

Once the program is running and you select a week:

    N (New Game): Add a game (Favorite vs. Underdog) and input spread/conditions.

    A (Advanced GA): Generate optimized pick slates using the Genetic Algorithm.

    P (Print): View and save your final picks to a text file.

    U (Update): Mark games as won/lost/tied after they happen.

    S (Score): specific tiebreaker score prediction.

    L (Loser): Pick a Survivor/Non-winner team.

    V (View Slates): View previously generated GA slates.

File Overview

    nfl_main.py: Run this file. It handles the user interface and game inputs.

    db_commands.py: Run this separately to view stats, backup, or clean the database ('''python3 db_commands.py''').

    nflpick.py: Contains the math, genetic algorithm, and normalization logic.

Logic

    Adjustments: Spreads are automatically adjusted for rest, 3-game win streaks, and division rivalries.

    Optimization: The GA generates 5 unique slates by evolving a population of 500 potential pick combinations over 300 generations.

Requirements

    Python 3.x