import subprocess
import sys
import os
import tempfile
import re
from typing import Dict, List, Tuple, Set

class ChampionsDrawEvaluator:
    def __init__(self):
        self.max_teams_per_country = {
            "Spain": 2, "England": 2, "Italy": 2,
            "Germany": 2, "France": 2
        }
        self.pots = {
            1: [("Real Madrid", "Spain"), ("Barcelona", "Spain"), ("PSG", "France"),
                ("Chelsea", "England"), ("Liverpool", "England"), ("Inter Milan", "Italy"),
                ("Manchester City", "England"), ("Bayern Munchen", "Germany"), ("Borussia Dortmund", "Germany")],
            2: [("Club Bruges", "Belgium"), ("Atletico Madrid", "Spain"), ("Sporting CP", "Portugal"),
                ("PSV", "Netherlands"), ("Ajax", "Netherlands"), ("Eintracht Frankfurt", "Germany"),
                ("Arsenal", "England"), ("Juventus", "Italy"), ("Villareal", "Spain")],
            3: [("Atalanta", "Italy"), ("Tottenham", "England"), ("Napoli", "Italy"),
                ("Marseille", "France"), ("Galatasaray", "Turkey"), ("Basel", "Switzerland"),
                ("Slavia Praga", "Czech Republic"), ("Bayer Leverkusen", "Germany"), ("Olympiacos", "Greece")],
            4: [("Qarabag", "Azerbaijan"), ("Copenhagen", "Denmark"), ("Athletic Bilbao", "Spain"),
                ("Dinamo Kyiv", "Ukraine"), ("Monaco", "France"), ("Union SG", "Belgium"),
                ("Salzburg", "Austria"), ("Newcastle", "England"), ("Lech Poznan", "Poland")]
        }
        self.all_teams = {team[0]: team[1] for pot in self.pots.values() for team in pot}

    def evaluate_py_file_with_cpp(self, py_file_path: str) -> Dict[str, float]:
        if not os.path.exists(py_file_path):
            return self._error_result("Python file not found")

        try:
            with open(py_file_path, 'r') as f:
                content = f.read()
            cpp_code = self._extract_cpp_from_python(content)
            if not cpp_code:
                return self._error_result("No valid C++ code found in Python file")
            return self.evaluate_code(cpp_code)
        except Exception as e:
            return self._error_result(f"Error processing Python file: {str(e)}")

    def _extract_cpp_from_python(self, py_content: str) -> str:
        matches = re.findall(r'"""(.*?)"""', py_content, re.DOTALL)
        if matches:
            return matches[-1]
        matches = re.findall(r'(?:#|//)\s*BEGIN CPP CODE(.*?)(?:#|//)\s*END CPP CODE', py_content, re.DOTALL)
        if matches:
            return matches[-1]
        if any(keyword in py_content for keyword in ['#include', 'using namespace', 'int main', 'cout', 'cin']):
            return py_content
        return ""

    def evaluate_code(self, cpp_code: str) -> Dict[str, float]:
        with tempfile.NamedTemporaryFile(suffix='.cpp', mode='w', delete=False) as f:
            f.write(cpp_code)
            cpp_path = f.name
        try:
            return self.evaluate(cpp_path)
        finally:
            try:
                os.unlink(cpp_path)
            except:
                pass

    def compile_and_run(self, cpp_path: str) -> Tuple[bool, str, int]:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                executable = os.path.join(temp_dir, "champions_draw")
                compile_result = subprocess.run(
                    ["g++", cpp_path, "-o", executable],
                    capture_output=True, text=True
                )
                if compile_result.returncode != 0:
                    return False, f"Compilation failed:\n{compile_result.stderr}", 0
                run_result = subprocess.run(
                    [executable], capture_output=True, text=True, timeout=30
                )
                if run_result.returncode != 0:
                    return False, f"Runtime error:\n{run_result.stderr}", 0
                return True, run_result.stdout, 0
        except subprocess.TimeoutExpired:
            return False, "Program timed out after 30 seconds", 0
        except Exception as e:
            return False, f"Error: {str(e)}", 0

    def parse_output(self, output: str) -> Dict[str, Dict[str, List[str]]]:
        calendar = {}
        # Split lines and process each team entry
        for line in output.split('\n'):
            line = line.strip()
            if not line.startswith("Team:"):
                continue
            
        # Extract team name and matches using regex
            match = re.match(
                r'Team:\s*(.*?)\s*\|\s*Home vs:\s*(.*?)\s*\|\s*Away vs:\s*(.*?)\s*$', 
                line
            )
            if not match:
                continue
            
            team_name = match.group(1)
            home_opponent = match.group(2)
            away_opponent = match.group(3)
        
            # Initialize team's matches dictionary if not exists
            if team_name not in calendar:
                calendar[team_name] = {}
        
            # Since the pot information isn't in this output format,
            # we'll store all matches under a "all" key or similar
            # Alternatively, we could modify this if pot info is available elsewhere
            calendar[team_name]["all"] = [home_opponent, away_opponent]
    
        return calendar

    def validate_calendar(self, calendar: Dict, ta: int) -> Dict[str, float]:
        metrics = {
            "valid": 1.0, "complete": 1.0,
            "country_rules": 1.0, "country_rules2": 1.0,
            "no_duplicates": 1.0, "same_adv": 1.0,
            "all_matches": 1.0, "ta_value": ta
        }

        if not calendar:
            return {k: 0.0 for k in metrics if k != "ta_value"} | {"ta_value": ta}

        all_matches = {team: [] for team in calendar}
        opponent_counts = {team: {} for team in calendar}

        # Costruisce la lista delle partite per ogni squadra
        for team, pots in calendar.items():
            for pot_matches in pots.values():
                all_matches[team].extend(pot_matches)
                for opponent in pot_matches:
                    opponent_counts[team][opponent] = opponent_counts[team].get(opponent, 0) + 1

        seen_pairs = set()
        total_teams = len(all_matches)
        expected_matches_per_team = 2  # Home e away

        teams_with_correct_matches = sum(
        1 for matches in all_matches.values()
        if len(matches) == 2 and all(opponent.strip() != "" for opponent in matches)
        )

        #  Calcola la metrica all_matches in modo proporzionale
        if total_teams == 0:
            metrics["all_matches"] = 0.0
        else:
            metrics["all_matches"] = teams_with_correct_matches / total_teams

        # Stampa di debug (puoi rimuoverla dopo)
        #print(f"Teams with correct matches: {teams_with_correct_matches}/{total_teams}")
        #for team, matches in all_matches.items():
            #print(f"{team}: {matches}")

        # Resto delle regole
        for team, matches in all_matches.items():
            country = self.all_teams.get(team, "")

            if team in matches:
                metrics["valid"] = 0.0

            if country in self.max_teams_per_country:
                same_country = sum(1 for opp in matches if self.all_teams.get(opp, "") == country)
                if same_country > self.max_teams_per_country[country]:
                    metrics["country_rules"] = 0.0

            if any(self.all_teams.get(opp, "") == country for opp in matches):
                metrics["country_rules2"] = 0.0

            for opponent in matches:
                if opponent not in all_matches or team not in all_matches[opponent]:
                    metrics["valid"] = 0.0
                pair = frozenset({team, opponent})
                if pair in seen_pairs:
                    metrics["no_duplicates"] = 0.0
                seen_pairs.add(pair)
                if opponent_counts[team].get(opponent, 0) > 1:
                    metrics["same_adv"] = 0.0

        # Completeness: se non tutte le squadre hanno due partite, la metrica complete va a 0
        if teams_with_correct_matches != total_teams:
            metrics["complete"] = 0.0

        # Combinazione delle metriche
        weights = {
            "valid": 0.00, "complete": 0.07,
            "country_rules": 0.10, "country_rules2": 0.10,
            "no_duplicates": 0.00, "same_adv": 0.07,
            "all_matches": 0.66
        }
        metrics["combined_score"] = sum(metrics[k] * weights[k] for k in weights)
        return metrics


    def evaluate(self, cpp_path: str) -> Dict[str, float]:
        if not os.path.exists(cpp_path):
            return self._error_result("File not found")
        success, output, ta = self.compile_and_run(cpp_path)
        if not success:
            return self._error_result(output)
        try:
            calendar = self.parse_output(output)
            metrics = self.validate_calendar(calendar, ta)
            metrics["error"] = 0.0
            return metrics
        except Exception as e:
            return self._error_result(f"Evaluation error: {str(e)}")

    def _error_result(self, message: str) -> Dict[str, float]:
        return {
            "valid": 0.0, "complete": 0.0,
            "country_rules": 0.0, "country_rules2": 0.0,
            "no_duplicates": 0.0, "same_adv": 0.0,
            "all_matches": 0.0, "combined_score": 0.0,
            "error": 1.0, "error_message": message, "ta_value": 0
        }

def score(cpp_path: str) -> float:
    evaluator = ChampionsDrawEvaluator()
    metrics = evaluator.evaluate(cpp_path)
    _print_metrics(metrics)
    return metrics.get("combined_score", 0.0)

def score_code(cpp_code: str) -> float:
    evaluator = ChampionsDrawEvaluator()
    metrics = evaluator.evaluate_code(cpp_code)
    _print_metrics(metrics)
    return metrics.get("combined_score", 0.0)

def score_py_file(py_file_path: str) -> float:
    evaluator = ChampionsDrawEvaluator()
    metrics = evaluator.evaluate_py_file_with_cpp(py_file_path)
    _print_metrics(metrics)
    return metrics.get("combined_score", 0.0)

def _print_metrics(metrics: Dict[str, float]):
    print("\nEvaluation Metrics:")
    print(f"Complete: {metrics['complete']}")
    print(f"Country Rules (max 2): {metrics['country_rules']}")
    print(f"Country Rules 2 (no same country): {metrics['country_rules2']}")
    print(f"Same Adversary: {metrics['same_adv']}")
    print(f"All Matches: {metrics['all_matches']}")
    print(f"Total Score: {metrics['combined_score']}")
    if metrics['error'] > 0:
        print(f"Error: {metrics.get('error_message', 'Unknown error')}")

def evaluate_s(cpp_path: str) -> dict:
    evaluator = ChampionsDrawEvaluator()
    return evaluator.evaluate(cpp_path)

def evaluate_code(cpp_code: str) -> dict:
    evaluator = ChampionsDrawEvaluator()
    return evaluator.evaluate_code(cpp_code)

def evaluate(py_file_path: str) -> dict:
    evaluator = ChampionsDrawEvaluator()
    return evaluator.evaluate_py_file_with_cpp(py_file_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ev518.py <path_to_file>")
        print("The file can be:")
        print("  - A .cpp file with C++ code")
        print("  - A .py file containing C++ code")
        print("  - Direct C++ code as string")
        sys.exit(1)

    input_arg = sys.argv[1]

    if os.path.exists(input_arg):
        if input_arg.endswith('.py'):
            result = score_py_file(input_arg)
        else:
            result = score(input_arg)
    else:
        result = score_code(input_arg)

    print(f"\nFinal Score: {result}")
