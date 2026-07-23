import re
import csv
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, List, Set, Tuple

def extract_resolved_player_names(log_file: str) -> Tuple[List[str], List[str]]:
    """Extract all resolved player names from the draft log file.
    
    Returns:
        Tuple of (non_defense_names, defense_names)
    """
    non_defense_names = []
    defense_names = []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all NAME_UPDATE entries
    pattern = r'NAME_UPDATE: Pick \d+, (-?\d+) -> (.+)'
    matches = re.findall(pattern, content)
    
    for player_id, name in matches:
        name = name.strip()
        # Skip entries that are just player IDs
        if not name.startswith('Player #'):
            # Negative IDs indicate defenses
            if int(player_id) < 0:
                defense_names.append(name)
            else:
                non_defense_names.append(name)
    
    return non_defense_names, defense_names

def load_csv_players(csv_file: str, player_column: str) -> Set[str]:
    """Load player names from a CSV file."""
    players = set()
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if player_column in row and row[player_column].strip():
                players.add(row[player_column].strip())
    
    return players

def normalize_player_name(name: str) -> str:
    """Normalize player name to handle common format variations."""
    # Remove common suffixes that cause mismatches
    name = name.replace(' Jr.', '').replace(' Sr.', '').replace(' III', '').replace(' II', '')
    
    # Handle specific punctuation variations
    name = name.replace('DJ ', 'D.J. ')
    
    # Strip any extra whitespace
    name = name.strip()
    
    return name

def create_defense_mappings() -> Tuple[Dict[str, str], Dict[str, str]]:
    """Create mappings for defense teams across different CSV formats.
    
    Returns:
        Tuple of (espn_to_def_csv, espn_to_adp_csv) mappings
    """
    # ESPN format -> DEF stats CSV format
    espn_to_def_csv = {
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
    
    # ESPN format -> ADP rankings CSV format
    espn_to_adp_csv = {
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
    
    return espn_to_def_csv, espn_to_adp_csv

def find_closest_matches(target: str, candidates: Set[str], threshold: float = 0.6) -> List[Tuple[str, float]]:
    """Find closest matches using fuzzy string matching."""
    matches = []
    
    for candidate in candidates:
        similarity = SequenceMatcher(None, target.lower(), candidate.lower()).ratio()
        if similarity >= threshold:
            matches.append((candidate, similarity))
    
    return sorted(matches, key=lambda x: x[1], reverse=True)

def analyze_player_matching():
    """Main analysis function."""
    print("="*80)
    print("PLAYER NAME MAPPING ANALYSIS")
    print("="*80)
    
    # File paths  
    log_file = "draftOps/test_logs/draft_monitor_fixed_20250831_195554.log"
    adp_file = "draftOps/playerData/ADP_Fantasy_Football_Rankings_2025.csv"
    non_def_file = "draftOps/playerData/Non_DEF_stats_ppr_6ptPaTD.csv"
    def_file = "draftOps/playerData/DEF_stats_ppr_6ptPaTD.csv"
    
    # Extract resolved player names from logs
    print("\n1. EXTRACTING PLAYER NAMES FROM DRAFT LOGS")
    print("-" * 50)
    
    non_defense_names, defense_names = extract_resolved_player_names(log_file)
    total_names = len(non_defense_names) + len(defense_names)
    
    print(f"Found {total_names} resolved player names:")
    print(f"  Non-defense players: {len(non_defense_names)}")
    print(f"  Defense teams: {len(defense_names)}")
    
    if non_defense_names:
        print("\n  Non-defense players:")
        for i, name in enumerate(non_defense_names, 1):
            print(f"    {i:2d}. {name}")
    
    if defense_names:
        print("\n  Defense teams:")
        for i, name in enumerate(defense_names, 1):
            print(f"    {i:2d}. {name}")
    
    # Load player data from CSV files
    print("\n2. LOADING PLAYER DATA FROM CSV FILES")
    print("-" * 50)
    
    adp_players = load_csv_players(adp_file, "Player")
    non_def_players = load_csv_players(non_def_file, "Player")
    def_teams = load_csv_players(def_file, "Team Defense")
    
    print(f"ADP Rankings CSV: {len(adp_players)} players")
    print(f"Non-DEF Stats CSV: {len(non_def_players)} players") 
    print(f"DEF Stats CSV: {len(def_teams)} defense teams")
    
    # Test exact matching
    print("\n3. EXACT MATCHING ANALYSIS")
    print("-" * 50)
    
    all_matches = []
    all_misses = []
    
    # NON-DEFENSE MATCHING
    if non_defense_names:
        print("\nNON-DEFENSE PLAYER MATCHING:")
        print("=" * 40)
        
        # ADP Rankings matching
        adp_exact_matches = []
        adp_normalized_matches = []
        adp_misses = []
        
        # Filter out defense entries from ADP CSV for non-defense matching
        adp_non_defense_players = {p for p in adp_players if not any(p.endswith(' ' + team) for team in ['Cardinals', 'Falcons', 'Ravens', 'Bills', 'Panthers', 'Bears', 'Bengals', 'Browns', 'Cowboys', 'Broncos', 'Lions', 'Packers', 'Texans', 'Colts', 'Jaguars', 'Chiefs', 'Raiders', 'Chargers', 'Rams', 'Dolphins', 'Vikings', 'Patriots', 'Saints', 'Giants', 'Jets', 'Eagles', 'Steelers', 'Seahawks', '49ers', 'Buccaneers', 'Titans', 'Commanders'])}
        
        for name in non_defense_names:
            if name in adp_non_defense_players:
                adp_exact_matches.append(name)
                all_matches.append(name)
            else:
                # Try normalized matching
                normalized_name = normalize_player_name(name)
                # Check if normalized version matches any player in CSV
                matching_players = [p for p in adp_non_defense_players if normalize_player_name(p) == normalized_name]
                if matching_players:
                    adp_normalized_matches.append((name, matching_players[0]))
                    all_matches.append(name)
                else:
                    adp_misses.append(name)
                    all_misses.append(name)
        
        total_adp_matches = len(adp_exact_matches) + len(adp_normalized_matches)
        
        print(f"\nADP Rankings CSV:")
        print(f"  Total matches: {total_adp_matches}/{len(non_defense_names)} ({total_adp_matches/len(non_defense_names)*100:.1f}%)")
        print(f"    Exact matches: {len(adp_exact_matches)}")
        print(f"    Normalized matches: {len(adp_normalized_matches)}")
        
        if adp_exact_matches:
            print("  [SUCCESS] Exact matches:")
            for name in adp_exact_matches[:5]:  # Show first 5
                print(f"    - {name}")
            if len(adp_exact_matches) > 5:
                print(f"    ... and {len(adp_exact_matches) - 5} more")
        
        if adp_normalized_matches:
            print("  [NORMALIZED] Normalized matches:")
            for espn_name, csv_name in adp_normalized_matches:
                print(f"    - '{espn_name}' -> '{csv_name}'")
        
        if adp_misses:
            print("  [FAILED] Failed matches:")
            for name in adp_misses:
                print(f"    - {name}")
        
        # Non-DEF Stats matching
        non_def_exact_matches = []
        non_def_normalized_matches = []
        non_def_misses = []
        
        for name in non_defense_names:
            if name in non_def_players:
                non_def_exact_matches.append(name)
            else:
                # Try normalized matching
                normalized_name = normalize_player_name(name)
                # Check if normalized version matches any player in CSV
                matching_players = [p for p in non_def_players if normalize_player_name(p) == normalized_name]
                if matching_players:
                    non_def_normalized_matches.append((name, matching_players[0]))
                else:
                    non_def_misses.append(name)
        
        total_non_def_matches = len(non_def_exact_matches) + len(non_def_normalized_matches)
        
        print(f"\nNon-DEF Stats CSV:")
        print(f"  Total matches: {total_non_def_matches}/{len(non_defense_names)} ({total_non_def_matches/len(non_defense_names)*100:.1f}%)")
        print(f"    Exact matches: {len(non_def_exact_matches)}")
        print(f"    Normalized matches: {len(non_def_normalized_matches)}")
        
        if non_def_exact_matches:
            print("  [SUCCESS] Exact matches:")
            for name in non_def_exact_matches[:5]:  # Show first 5
                print(f"    - {name}")
            if len(non_def_exact_matches) > 5:
                print(f"    ... and {len(non_def_exact_matches) - 5} more")
        
        if non_def_normalized_matches:
            print("  [NORMALIZED] Normalized matches:")
            for espn_name, csv_name in non_def_normalized_matches:
                print(f"    - '{espn_name}' -> '{csv_name}'")
        
        if non_def_misses:
            print("  [FAILED] Failed matches:")
            for name in non_def_misses:
                print(f"    - {name}")
    
    # DEFENSE MATCHING
    if defense_names:
        print("\nDEFENSE TEAM MATCHING:")
        print("=" * 40)
        
        espn_to_def_csv, espn_to_adp_csv = create_defense_mappings()
        
        # Direct matching (ESPN format vs CSV)
        def_direct_matches = []
        def_direct_misses = []
        
        for name in defense_names:
            if name in def_teams:
                def_direct_matches.append(name)
            else:
                def_direct_misses.append(name)
        
        print(f"\nDirect matching (ESPN format vs CSV):")
        print(f"  Exact matches: {len(def_direct_matches)}/{len(defense_names)} ({len(def_direct_matches)/len(defense_names)*100:.1f}%)")
        
        if def_direct_matches:
            print("  [SUCCESS] Direct matches:")
            for name in def_direct_matches:
                print(f"    - {name}")
        
        if def_direct_misses:
            print("  [FAILED] Direct misses:")
            for name in def_direct_misses:
                print(f"    - {name}")
        
        # ADP Rankings defense matching (ESPN -> ADP format conversion)
        adp_def_mapped_matches = []
        adp_def_mapped_misses = []
        
        for name in defense_names:
            mapped_name = espn_to_adp_csv.get(name)
            if mapped_name and mapped_name in adp_players:
                adp_def_mapped_matches.append((name, mapped_name))
            else:
                adp_def_mapped_misses.append((name, mapped_name))
        
        print(f"\nADP Rankings defense matching (ESPN -> ADP format):")
        print(f"  Mapped matches: {len(adp_def_mapped_matches)}/{len(defense_names)} ({len(adp_def_mapped_matches)/len(defense_names)*100:.1f}%)")
        
        if adp_def_mapped_matches:
            print("  [SUCCESS] ADP defense matches:")
            for espn_name, adp_name in adp_def_mapped_matches:
                print(f"    - '{espn_name}' -> '{adp_name}'")
        
        if adp_def_mapped_misses:
            print("  [FAILED] ADP mapping failures:")
            for espn_name, adp_name in adp_def_mapped_misses:
                print(f"    - '{espn_name}' -> '{adp_name}' (not found in ADP CSV)")
        
        # DEF Stats CSV matching (ESPN -> DEF format conversion)
        def_mapped_matches = []
        def_mapped_misses = []
        
        for name in defense_names:
            mapped_name = espn_to_def_csv.get(name)
            if mapped_name and mapped_name in def_teams:
                def_mapped_matches.append((name, mapped_name))
                all_matches.append(name)
            else:
                def_mapped_misses.append((name, mapped_name))
                all_misses.append(name)
        
        print(f"\nDEF Stats CSV matching (ESPN -> DEF format):")
        print(f"  Mapped matches: {len(def_mapped_matches)}/{len(defense_names)} ({len(def_mapped_matches)/len(defense_names)*100:.1f}%)")
        
        if def_mapped_matches:
            print("  [SUCCESS] DEF stats matches:")
            for espn_name, csv_name in def_mapped_matches:
                print(f"    - '{espn_name}' -> '{csv_name}'")
        
        if def_mapped_misses:
            print("  [FAILED] DEF mapping failures:")
            for espn_name, csv_name in def_mapped_misses:
                print(f"    - '{espn_name}' -> '{csv_name}' (not found in DEF CSV)")
    
    else:
        print("\nDEFENSE ANALYSIS:")
        print("=" * 40)
        print("  No defense picks found in sample data")
    
    # Fuzzy matching recommendations
    print("\n4. FUZZY MATCHING RECOMMENDATIONS")
    print("-" * 50)
    
    if all_misses:
        print("Analyzing failed matches for fuzzy matching opportunities...")
        
        for missed_name in all_misses:
            print(f"\nFailed match: '{missed_name}'")
            
            # For non-defense players
            if missed_name in non_defense_names:
                # Try ADP candidates
                adp_candidates = find_closest_matches(missed_name, adp_players, threshold=0.7)
                if adp_candidates:
                    print(f"  ADP suggestions:")
                    for candidate, score in adp_candidates[:3]:  # Top 3
                        print(f"    - {candidate} (similarity: {score:.3f})")
                
                # Try Non-DEF candidates  
                non_def_candidates = find_closest_matches(missed_name, non_def_players, threshold=0.7)
                if non_def_candidates:
                    print(f"  Non-DEF suggestions:")
                    for candidate, score in non_def_candidates[:3]:  # Top 3
                        print(f"    - {candidate} (similarity: {score:.3f})")
            
            # For defense players
            elif missed_name in defense_names:
                # Try defense candidates
                def_candidates = find_closest_matches(missed_name, def_teams, threshold=0.7)
                if def_candidates:
                    print(f"  Defense suggestions:")
                    for candidate, score in def_candidates[:3]:  # Top 3
                        print(f"    - {candidate} (similarity: {score:.3f})")
    else:
        print("[SUCCESS] No fuzzy matching needed - all names matched exactly!")
    
    # Final recommendations
    print("\n5. FINAL RECOMMENDATIONS")
    print("-" * 50)
    
    total_matches = len(all_matches)
    total_names = len(non_defense_names) + len(defense_names)
    overall_success_rate = total_matches / total_names * 100 if total_names > 0 else 0
    
    print(f"Overall matching success rate: {total_matches}/{total_names} ({overall_success_rate:.1f}%)")
    
    # Separate analysis for non-defense vs defense
    non_def_success_rate = 100.0 if non_defense_names and len([n for n in non_defense_names if n in all_matches]) == len(non_defense_names) else 0
    def_success_rate = 100.0 if defense_names and len([n for n in defense_names if n in all_matches]) == len(defense_names) else 0
    
    if non_defense_names:
        non_def_matched = len([n for n in non_defense_names if n in all_matches])
        print(f"  Non-defense success: {non_def_matched}/{len(non_defense_names)} ({non_def_success_rate:.1f}%)")
    
    if defense_names:
        def_matched = len([n for n in defense_names if n in all_matches])
        print(f"  Defense success: {def_matched}/{len(defense_names)} ({def_success_rate:.1f}%)")
    
    # Enhanced recommendations based on normalization results
    print(f"\nPERFORMANCE IMPROVEMENT ANALYSIS:")
    print("=" * 50)
    
    if non_defense_names:
        exact_only_rate = len([n for n in non_defense_names if n in adp_players or n in non_def_players]) / len(non_defense_names) * 100
        with_normalization_rate = total_adp_matches / len(non_defense_names) * 100
        improvement = with_normalization_rate - exact_only_rate
        
        print(f"Non-defense matching improvement:")
        print(f"  Exact matching only: {exact_only_rate:.1f}%")
        print(f"  With normalization: {with_normalization_rate:.1f}%")
        print(f"  Improvement: +{improvement:.1f} percentage points")
    
    # Recommendations based on results
    if overall_success_rate >= 98:
        print("\n[RECOMMENDATION] Enhanced matching strategy is highly effective")
        
        if non_defense_names:
            print("   - Non-defense: Use exact matching + name normalization")
            print("     * Handles suffixes (Jr., Sr., III, II)")
            print("     * Handles punctuation variations (DJ -> D.J.)")
            print("     * Achieves near-perfect matching")
        
        if defense_names and def_success_rate >= 95:
            print("   - Defense: Team name mapping dictionary is mandatory")
            print("     * ESPN format: 'TEAM DST' (e.g., 'PIT DST')")
            print("     * CSV format: 'Team Name' (e.g., 'Steelers')")
        
        print("   - Minimal fuzzy matching needed for edge cases")
        
    elif overall_success_rate >= 95:
        print("\n[RECOMMENDATION] Current approach is sufficient with minor enhancements")
        
        if non_defense_names and with_normalization_rate >= 98:
            print("   - Non-defense: Name normalization significantly improves matching")
        
        if defense_names and def_success_rate >= 95:
            print("   - Defense: Team name mapping dictionary is needed")
            print("     * ESPN format: 'TEAM DST' (e.g., 'PIT DST')")
            print("     * CSV format: 'Team Name' (e.g., 'Steelers')")
        
        print("   - Consider adding basic fuzzy matching as fallback for edge cases")
        
    elif overall_success_rate >= 80:
        print("\n[WARNING] Partial matching success - implement targeted solutions")
        
        if non_defense_names and non_def_success_rate < 80:
            print("   - Non-defense: Add fuzzy matching for player names")
        
        if defense_names and def_success_rate < 80:
            print("   - Defense: Fix team name mapping dictionary")
            print("   - Defense: Add fuzzy matching for unmapped teams")
        
        print("   - Monitor failed matches for patterns")
        
    else:
        print("\n[CRITICAL] Major mapping issues detected")
        print("   - Implement comprehensive name normalization")
        print("   - Create robust mapping dictionaries")
        print("   - Add multi-algorithm fuzzy matching")
        print("   - Consider manual override mechanisms")
    
    print("\n[IMPLEMENTATION GUIDE] Enhanced Player Matching:")
    print("=" * 50)
    
    if non_defense_names and with_normalization_rate > exact_only_rate:
        print("1. Name Normalization Function:")
        print("   def normalize_player_name(name: str) -> str:")
        print("       # Remove common suffixes")
        print("       name = name.replace(' Jr.', '').replace(' Sr.', '').replace(' III', '')")
        print("       # Handle punctuation variations")
        print("       name = name.replace('DJ ', 'D.J. ')")
        print("       return name.strip()")
        print("")
    
    if defense_names and def_success_rate >= 95:
        print("2. Defense Team Mapping (Multiple CSV formats):")
        print("   # For ADP Rankings CSV")
        print("   def get_adp_defense_name(espn_defense_name: str) -> str:")
        print("       mapping = {")
        print("           'PIT DST': 'Pittsburgh Steelers',")
        print("           'DEN DST': 'Denver Broncos',")
        print("           # ... (full city + team name)")
        print("       }")
        print("       return mapping.get(espn_defense_name, espn_defense_name)")
        print("")
        print("   # For DEF Stats CSV")
        print("   def get_def_stats_name(espn_defense_name: str) -> str:")
        print("       mapping = {")
        print("           'PIT DST': 'Steelers',")
        print("           'DEN DST': 'Broncos',")
        print("           # ... (team name only)")
        print("       }")
        print("       return mapping.get(espn_defense_name, espn_defense_name)")
        print("")
    
    print("3. Complete Matching Strategy:")
    print("   def find_player_in_csv(espn_name: str, csv_players: Set[str]) -> str:")
    print("       # 1. Try exact match first")
    print("       if espn_name in csv_players:")
    print("           return espn_name")
    print("       # 2. Try normalized match")
    print("       normalized = normalize_player_name(espn_name)")
    print("       for csv_player in csv_players:")
    print("           if normalize_player_name(csv_player) == normalized:")
    print("               return csv_player")
    print("       # 3. Player not found")
    print("       return None")
    
    if total_names < 50:
        print(f"\n[NOTE] Analysis based on limited sample ({total_names} names)")
        print("   - Consider running full draft simulation for comprehensive analysis")
        print("   - Monitor real draft logs for additional edge cases")

if __name__ == "__main__":
    analyze_player_matching()