#!/usr/bin/env python3
"""
Player Data Loader for DraftOps

Loads player data from CSV files and creates unified Player objects
for use during draft decision making.

Handles:
- ADP data from consensus rankings
- Offensive player projections (QB, RB, WR, TE, K) 
- Defensive team projections (DST)
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set
import re


def normalize_player_name(name: str) -> str:
    """Normalize player name for consistent matching."""
    name = name.replace(' Jr.', '').replace(' Sr.', '')
    name = name.replace(' III', '').replace(' II', '')
    name = name.replace('DJ ', 'D.J. ')
    return name.strip()


# ESPN format -> ADP CSV format
ESPN_TO_ADP_DEFENSE = {
    'ARI DST': 'Arizona Cardinals',
    'ATL DST': 'Atlanta Falcons', 
    'BAL DST': 'Baltimore Ravens',
    'BUF DST': 'Buffalo Bills',
    'CAR DST': 'Carolina Panthers',
    'CHI DST': 'Chicago Bears',
    'CIN DST': 'Cincinnati Bengals',
    'CLE DST': 'Cleveland Browns',
    'DAL DST': 'Dallas Cowboys',
    'DEN DST': 'Denver Broncos',
    'DET DST': 'Detroit Lions',
    'GB DST': 'Green Bay Packers',
    'HOU DST': 'Houston Texans',
    'IND DST': 'Indianapolis Colts',
    'JAX DST': 'Jacksonville Jaguars',
    'KC DST': 'Kansas City Chiefs',
    'LAS DST': 'Las Vegas Raiders',
    'LAC DST': 'Los Angeles Chargers',
    'LAR DST': 'Los Angeles Rams',
    'MIA DST': 'Miami Dolphins',
    'MIN DST': 'Minnesota Vikings',
    'NE DST': 'New England Patriots',
    'NO DST': 'New Orleans Saints',
    'NYG DST': 'New York Giants',
    'NYJ DST': 'New York Jets',
    'PHI DST': 'Philadelphia Eagles',
    'PIT DST': 'Pittsburgh Steelers',
    'SEA DST': 'Seattle Seahawks',
    'SF DST': 'San Francisco 49ers',
    'TB DST': 'Tampa Bay Buccaneers',
    'TEN DST': 'Tennessee Titans',
    'WAS DST': 'Washington Commanders'
}

# ESPN format -> DEF Stats CSV format  
ESPN_TO_DEF_STATS = {
    'ARI DST': 'Cardinals',
    'ATL DST': 'Falcons', 
    'BAL DST': 'Ravens',
    'BUF DST': 'Bills',
    'CAR DST': 'Panthers',
    'CHI DST': 'Bears',
    'CIN DST': 'Bengals',
    'CLE DST': 'Browns',
    'DAL DST': 'Cowboys',
    'DEN DST': 'Broncos',
    'DET DST': 'Lions',
    'GB DST': 'Packers',
    'HOU DST': 'Texans',
    'IND DST': 'Colts',
    'JAX DST': 'Jaguars',
    'KC DST': 'Chiefs',
    'LAS DST': 'Raiders',
    'LAC DST': 'Chargers',
    'LAR DST': 'Rams',
    'MIA DST': 'Dolphins',
    'MIN DST': 'Vikings',
    'NE DST': 'Patriots',
    'NO DST': 'Saints',
    'NYG DST': 'Giants',
    'NYJ DST': 'Jets',
    'PHI DST': 'Eagles',
    'PIT DST': 'Steelers',
    'SEA DST': 'Seahawks',
    'SF DST': '49ers',
    'TB DST': 'Buccaneers',
    'TEN DST': 'Titans',
    'WAS DST': 'Commanders'
}


@dataclass
class Player:
    """Represents a draftable player with all relevant data."""
    
    # Core identification
    name: str
    team: str
    position: str
    
    # Rankings and ADP
    adp_rank: int  # Overall ADP rank
    position_rank: int  # Position-specific rank (parsed from WR-01 format)
    adp_avg: float  # Average ADP across platforms
    adp_std: float  # Standard deviation of ADP
    
    # Projections
    fantasy_points: float
    
    # Key stats (optional, mainly for offensive players)
    pid: Optional[str] = None  # Player ID from stats file
    pass_yds: float = 0.0
    pass_td: int = 0
    rush_yds: float = 0.0
    rush_td: int = 0
    receptions: float = 0.0
    rec_yds: float = 0.0
    rec_td: int = 0
    
    # Defense-specific stats
    sacks: int = 0
    turnovers: int = 0
    
    def __str__(self) -> str:
        return f"{self.name} ({self.position}{self.position_rank:02d}) - ADP: {self.adp_avg:.1f}, Proj: {self.fantasy_points:.1f}"


class PlayerDataLoader:
    """Loads and processes player data from CSV files."""
    
    def __init__(self, data_dir: str = "draftOps/playerData"):
        self.data_dir = Path(data_dir)
        self.logger = logging.getLogger(__name__)
        
        # File paths
        self.adp_file = self.data_dir / "ADP_Fantasy_Football_Rankings_2025.csv"
        self.offense_file = self.data_dir / "Non_DEF_stats_ppr_6ptPaTD.csv"
        self.defense_file = self.data_dir / "DEF_stats_ppr_6ptPaTD.csv"
        
    def load_all_players(self) -> List[Player]:
        """
        Load all players from CSV files and return unified Player objects.
        
        Returns:
            List of Player objects sorted by ADP rank
        """
        self.logger.info("Loading player data from CSV files...")
        
        # Load ADP data first (this is our master list)
        adp_data = self._load_adp_data()
        self.logger.info(f"Loaded {len(adp_data)} players from ADP file")
        
        # Load offensive player stats
        offense_stats = self._load_offense_stats()
        self.logger.info(f"Loaded {len(offense_stats)} offensive players from stats file")
        
        # Load defensive stats
        defense_stats = self._load_defense_stats()
        self.logger.info(f"Loaded {len(defense_stats)} defenses from stats file")
        
        # Merge data to create Player objects
        players = self._merge_player_data(adp_data, offense_stats, defense_stats)
        
        # Sort by ADP rank
        players.sort(key=lambda p: p.adp_rank)
        
        self._log_summary(players)
        return players
        
    def _load_adp_data(self) -> Dict[str, Dict]:
        """Load ADP data from CSV file."""
        adp_data = {}
        
        with open(self.adp_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                name = row['Player'].strip()
                position_code = row['Position'].strip()  # e.g., "WR-01"
                
                # Parse position and rank
                if '-' in position_code:
                    position, rank_str = position_code.split('-', 1)
                    position_rank = int(rank_str)
                else:
                    position = position_code
                    position_rank = 1
                    
                # Handle defense naming (convert to DST)
                if position == 'DEF' or position == 'DST' or 'Defense' in name:
                    position = 'DST'
                    
                adp_data[name] = {
                    'adp_rank': int(row['ADP']),
                    'position': position,
                    'position_rank': position_rank,
                    'team': row['Team'].strip(),
                    'adp_avg': float(row['Avg']),
                    'adp_std': float(row['Std Dev'])
                }
                
        return adp_data
        
    def _load_offense_stats(self) -> Dict[str, Dict]:
        """Load offensive player stats from CSV file."""
        offense_stats = {}
        
        with open(self.offense_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                name = row['Player'].strip()
                
                # Extract relevant stats
                offense_stats[name] = {
                    'pid': row['PID'],
                    'position': row['Pos'].strip(),
                    'team': row['Team'].strip(),
                    'fantasy_points': float(row['FF Pts']),
                    'pass_yds': float(row['Pass Yds']) if row['Pass Yds'] else 0.0,
                    'pass_td': int(float(row['Pass TD'])) if row['Pass TD'] else 0,
                    'rush_yds': float(row['Rush Yds']) if row['Rush Yds'] else 0.0,
                    'rush_td': int(float(row['Rush TD'])) if row['Rush TD'] else 0,
                    'receptions': float(row['Rec']) if row['Rec'] else 0.0,
                    'rec_yds': float(row['Rec Yds']) if row['Rec Yds'] else 0.0,
                    'rec_td': int(float(row['Rec TD'])) if row['Rec TD'] else 0
                }
                
        return offense_stats
        
    def _load_defense_stats(self) -> Dict[str, Dict]:
        """Load defensive team stats from CSV file."""
        defense_stats = {}
        
        with open(self.defense_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                team_name = row['Team Defense'].strip()
                
                # Standardize team defense names (remove "Defense" suffix)
                if team_name.endswith(' Defense'):
                    team_name = team_name[:-8].strip()  # Remove " Defense"
                
                defense_stats[team_name] = {
                    'position': 'DST',
                    'team': team_name.upper()[:3],  # Convert to 3-letter code
                    'fantasy_points': float(row['FF Pts']),
                    'sacks': int(row['Sacks']),
                    'turnovers': int(row['Forced Turnovers'])
                }
                
        return defense_stats
        
    def _merge_player_data(self, adp_data: Dict, offense_stats: Dict, defense_stats: Dict) -> List[Player]:
        """Merge ADP and stats data to create Player objects."""
        players = []
        unmatched_names = set()
        
        for name, adp_info in adp_data.items():
            position = adp_info['position']
            
            # Initialize player with ADP data
            player = Player(
                name=name,
                team=adp_info['team'],
                position=position,
                adp_rank=adp_info['adp_rank'],
                position_rank=adp_info['position_rank'],
                adp_avg=adp_info['adp_avg'],
                adp_std=adp_info['adp_std'],
                fantasy_points=0.0  # Will be updated from stats
            )
            
            # Try to match with stats data
            if position == 'DST':
                # Match defense by team name
                matched = False
                for def_name, def_stats in defense_stats.items():
                    if self._is_defense_match(name, def_name, adp_info['team']):
                        player.fantasy_points = def_stats['fantasy_points']
                        player.sacks = def_stats['sacks']
                        player.turnovers = def_stats['turnovers']
                        matched = True
                        break
                        
                if not matched:
                    unmatched_names.add(f"Defense: {name}")
                    
            else:
                # Match offensive player by name
                matched = False
                if name in offense_stats:
                    stats = offense_stats[name]
                    player.pid = stats['pid']
                    player.fantasy_points = stats['fantasy_points']
                    player.pass_yds = stats['pass_yds']
                    player.pass_td = stats['pass_td']
                    player.rush_yds = stats['rush_yds']
                    player.rush_td = stats['rush_td']
                    player.receptions = stats['receptions']
                    player.rec_yds = stats['rec_yds']
                    player.rec_td = stats['rec_td']
                    matched = True
                else:
                    # Try normalized name matching
                    normalized_name = normalize_player_name(name)
                    for stats_name, stats in offense_stats.items():
                        if normalize_player_name(stats_name) == normalized_name:
                            player.pid = stats['pid']
                            player.fantasy_points = stats['fantasy_points']
                            player.pass_yds = stats['pass_yds']
                            player.pass_td = stats['pass_td']
                            player.rush_yds = stats['rush_yds']
                            player.rush_td = stats['rush_td']
                            player.receptions = stats['receptions']
                            player.rec_yds = stats['rec_yds']
                            player.rec_td = stats['rec_td']
                            matched = True
                            break
                
                if not matched:
                    unmatched_names.add(f"Offense: {name}")
            
            players.append(player)
            
        if unmatched_names:
            self.logger.warning(f"Could not match {len(unmatched_names)} players with stats: {sorted(unmatched_names)[:10]}...")
            
        return players
        
    def _is_defense_match(self, adp_name: str, def_name: str, team_code: str) -> bool:
        """Check if ADP defense name matches stats defense name."""
        # First try ESPN defense mappings
        if adp_name in ESPN_TO_DEF_STATS:
            mapped_name = ESPN_TO_DEF_STATS[adp_name]
            if mapped_name == def_name:
                return True
        
        # Fallback to original matching logic
        adp_lower = adp_name.lower()
        def_lower = def_name.lower()
        
        # Direct match
        if def_name in adp_name or adp_name in def_name:
            return True
            
        # Team code match
        if team_code.lower() in def_lower:
            return True
            
        return False
        
    def _log_summary(self, players: List[Player]) -> None:
        """Log summary of loaded players."""
        position_counts = {}
        total_with_projections = 0
        
        for player in players:
            pos = player.position
            position_counts[pos] = position_counts.get(pos, 0) + 1
            if player.fantasy_points > 0:
                total_with_projections += 1
                
        self.logger.info(f"Loaded {len(players)} total players:")
        for pos, count in sorted(position_counts.items()):
            self.logger.info(f"  {pos}: {count}")
        self.logger.info(f"Players with fantasy point projections: {total_with_projections}")
        
        # Show top 10 players
        top_10 = players[:10]
        self.logger.info("Top 10 players by ADP:")
        for i, player in enumerate(top_10, 1):
            self.logger.info(f"  {i:2d}. {player}")


def load_player_data(data_dir: str = "draftOps/playerData") -> List[Player]:
    """
    Convenience function to load all player data.
    
    Args:
        data_dir: Directory containing CSV files
        
    Returns:
        List of Player objects sorted by ADP rank
    """
    loader = PlayerDataLoader(data_dir)
    return loader.load_all_players()


if __name__ == "__main__":
    # Test the loader
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    players = load_player_data()
    print(f"\nLoaded {len(players)} players successfully!")
    print("\nTop 5 by position:")
    
    positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
    for pos in positions:
        pos_players = [p for p in players if p.position == pos][:5]
        print(f"\n{pos}:")
        for i, player in enumerate(pos_players, 1):
            print(f"  {i}. {player}")