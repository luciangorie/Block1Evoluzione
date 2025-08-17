#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
using namespace std;

struct CalendarTeam {
    string name;
    string country;
    string t1 = ""; // home match opponent
    string t2 = ""; // away match opponent

    void print() const {
        cout << "Team: " << name
             << " | Home vs: " << t1
             << " | Away vs: " << t2 << endl;
    }
    // For convenience, get the number of matches assigned
    int matchesAssigned() const {
        int c = 0;
        if (!t1.empty()) ++c;
        if (!t2.empty()) ++c;
        return c;
    }
};


/**
 * Find possible opponents for a team for the given slot.
 * Only teams that do not break country rule and are not already paired.
 * If preferFewestMatches is true, prefer opponents with fewest matches assigned.
 */
vector<int> findPossibleOpponents(const CalendarTeam& team,
                                  const vector<CalendarTeam>& teams,
                                  const string& slot,
                                  bool preferFewestMatches = true) {
    vector<int> indices;
    for (int i = 0; i < teams.size(); ++i) {
        const auto& opp = teams[i];
        if (opp.name == team.name) continue;
        if (opp.country == team.country) continue;
        if ((team.t1 == opp.name || team.t2 == opp.name) ||
            (opp.t1 == team.name || opp.t2 == team.name)) continue;

        // Only allow if opponent has empty slot in the "mirrored" slot
        if (slot == "t1" && opp.t2 == "") indices.push_back(i);
        else if (slot == "t2" && opp.t1 == "") indices.push_back(i);
    }
    // Sort by (fewest matches assigned, then least available opponents) to reduce deadlock risk
    vector<tuple<int, int, int>> sort_vec; // (matchesAssigned, degree, idx)
    for (int idx : indices) {
        int degree = 0;
        for (int j = 0; j < teams.size(); ++j) {
            if (j == idx) continue;
            if (teams[j].country == teams[idx].country) continue;
            if ((teams[idx].t1 == teams[j].name || teams[idx].t2 == teams[j].name) ||
                (teams[j].t1 == teams[idx].name || teams[j].t2 == teams[idx].name)) continue;
            // Only count if mirrored slot available
            if (slot == "t1" && teams[j].t2 == "") ++degree;
            else if (slot == "t2" && teams[j].t1 == "") ++degree;
        }
        int matches = teams[idx].matchesAssigned();
        sort_vec.emplace_back(matches, degree, idx);
    }
    // Sort: prefer fewest matches assigned, then lowest degree
    sort(sort_vec.begin(), sort_vec.end());
    vector<int> result;
    for (auto& tup : sort_vec) result.push_back(get<2>(tup));
    return result;
}

/**
 * Lookahead function: after an assignment, check if every team can still get 2 matches.
 * Returns false if some team will be left out.
 * Also checks for duplicate matches.
 */
bool lookahead(const vector<CalendarTeam>& teams) {
    // For each team, count number of valid available opponents for each slot
    for (int i = 0; i < teams.size(); ++i) {
        const auto& team = teams[i];
        // Check for duplicate assignments (no two teams can have same opponent in both slots)
        if (!team.t1.empty() && team.t1 == team.t2) return false;
        if (team.t1 == "") {
            auto v = findPossibleOpponents(team, teams, "t1");
            if (v.empty()) return false;
        }
        if (team.t2 == "") {
            auto v = findPossibleOpponents(team, teams, "t2");
            if (v.empty()) return false;
        }
    }
    // Check for duplicate matches (A vs B, B vs A in both slots)
    for (int i = 0; i < teams.size(); ++i) {
        for (int j = i+1; j < teams.size(); ++j) {
            const auto& t1 = teams[i], &t2 = teams[j];
            if ((t1.t1 == t2.name && t2.t1 == t1.name) ||
                (t1.t2 == t2.name && t2.t2 == t1.name))
                return false;
        }
    }
    return true;
}

/**
 * Backtracking assignment with lookahead to avoid deadlocks.
 * Returns true if successful.
 * Now sorts teams by fewest matches assigned for better balancing.
 */
bool assignMatchesBT(vector<CalendarTeam>& teams, int idx = 0) {
    if (idx == teams.size()) {
        // All teams processed
        for (const auto& t : teams)
            if (t.t1 == "" || t.t2 == "")
                return false;
        // Final check: no duplicate matches
        for (int i = 0; i < teams.size(); ++i) {
            for (int j = i+1; j < teams.size(); ++j) {
                const auto& t1 = teams[i], &t2 = teams[j];
                if ((t1.t1 == t2.name && t2.t1 == t1.name) ||
                    (t1.t2 == t2.name && t2.t2 == t1.name))
                    return false;
            }
        }
        return true;
    }

    // Order teams by least matches assigned to improve fairness and avoid deadlocks
    vector<int> teamOrder;
    for (int i = idx; i < teams.size(); ++i) teamOrder.push_back(i);
    sort(teamOrder.begin(), teamOrder.end(), [&](int a, int b){
        return teams[a].matchesAssigned() < teams[b].matchesAssigned();
    });

    for (int ord = 0; ord < teamOrder.size(); ++ord) {
        int tIdx = teamOrder[ord];
        auto& team = teams[tIdx];
        if (team.t1 != "" && team.t2 != "") continue;

        // Try to assign t1 (home) first if needed
        if (team.t1 == "") {
            auto possibles = findPossibleOpponents(team, teams, "t1");
            for (int i : possibles) {
                if (teams[i].t2 != "") continue;
                // Assign
                team.t1 = teams[i].name;
                teams[i].t2 = team.name;
                if (lookahead(teams) && assignMatchesBT(teams, idx+1)) return true;
                // Backtrack
                team.t1 = "";
                teams[i].t2 = "";
            }
            // If we tried all and failed, continue to next team order (not fail yet)
        }
        // Try to assign t2 (away) if needed
        if (team.t2 == "") {
            auto possibles = findPossibleOpponents(team, teams, "t2");
            for (int i : possibles) {
                if (teams[i].t1 != "") continue;
                // Assign
                team.t2 = teams[i].name;
                teams[i].t1 = team.name;
                if (lookahead(teams) && assignMatchesBT(teams, idx+1)) return true;
                // Backtrack
                team.t2 = "";
                teams[i].t1 = "";
            }
        }
        // If we get here, assignment failed for this team at this idx
        return false;
    }
    // All teams at this idx processed
    return assignMatchesBT(teams, idx+1);
}

int main() {
    // For demonstration, using 9 teams from different countries (to maximize possible assignments)
    vector<CalendarTeam> teams = {
        {"PSG", "France"}, {"Dortmund", "Germany"}, {"Liverpool", "England"},
        {"Chelsea", "England"}, {"Real Madrid", "Spain"}, {"Juventus", "Italy"},
        {"Ajax", "Netherlands"}, {"Porto", "Portugal"}, {"Shakhtar", "Ukraine"}
    };

    // Shuffle teams for variety
    std::random_device rd;
    std::mt19937 g(rd());
    std::shuffle(teams.begin(), teams.end(), g);

    bool ok = assignMatchesBT(teams);

    if (!ok) {
        cout << "Could not assign matches for all teams without deadlock.\n";
    } else {
        cout << "Champions League Matches:\n";
        for (const auto& t : teams) {
            t.print();
        }
        // Print match list (to check for duplicates and completeness)
        cout << "\nMatch List:\n";
        vector<pair<string, string>> matches;
        for (const auto& t : teams) {
            if (!t.t1.empty())
                matches.emplace_back(t.name, t.t1);
            if (!t.t2.empty())
                matches.emplace_back(t.t2, t.name);
        }
        sort(matches.begin(), matches.end());
        for (auto& m : matches) {
            cout << m.first << " vs " << m.second << endl;
        }
    }
    return 0;
}
