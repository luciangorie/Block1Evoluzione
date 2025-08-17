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
};


// restituisce lista di avversari validi
vector<int> findPossibleOpponents(const CalendarTeam& team,
                                  const vector<CalendarTeam>& teams,
                                  const string& slot) {
    vector<int> indices;
    for (int i = 0; i < teams.size(); ++i) {
        const auto& opp = teams[i];
        if (opp.name == team.name) continue;
        if (opp.country == team.country) continue;
        if ((team.t1 == opp.name || team.t2 == opp.name) ||
            (opp.t1 == team.name || opp.t2 == team.name)) continue;

        if (slot == "t1" && opp.t2 == "") indices.push_back(i);
        else if (slot == "t2" && opp.t1 == "") indices.push_back(i);
    }
    return indices;
}

//#EVOLVE-BLOCK-START
bool lookahead(CalendarTeam& team, const vector<CalendarTeam>& teams)
{
    // This function is a placeholder for any future logic that might be needed
    // to look ahead in the schedule and to know if deadlocks will happen.
    return true; // For now, we assume no deadlocks are happening
}
//#EVOLVE-BLOCK-END

void assignMatches(vector<CalendarTeam>& teams) {
    random_device rd;
    mt19937 g(rd());

    for (auto& team : teams) {
        if (team.t1 == "") {
            auto possibles = findPossibleOpponents(team, teams, "t1");
            shuffle(possibles.begin(), possibles.end(), g);
            for (int i : possibles) {
                if (teams[i].t2 == "") {
                    team.t1 = teams[i].name;
                    teams[i].t2 = team.name;
                    break;
                }
            }
        }

        if (team.t2 == "") {
            auto possibles = findPossibleOpponents(team, teams, "t2");
            shuffle(possibles.begin(), possibles.end(), g);
            for (int i : possibles) {
                if (teams[i].t1 == "") {
                    team.t2 = teams[i].name;
                    teams[i].t1 = team.name;
                    break;
                }
            }
        }
        bool valid = lookahead(team, teams);
        if (!valid) {
            cout << "Invalid match assignment for team: " << team.name << endl;
            team.t1 = "";
            team.t2 = "";
        }
    }
}

int main() {
    vector<CalendarTeam> teams = {
         {"PSG", "France"},
        {"Dortmund", "Germany"}, {"Liverpool", "England"}, {"Chelsea", "England"}
    };

    assignMatches(teams);

    cout << "Champions League Matches:\n";
    for (const auto& t : teams) {
        t.print();
    }

    return 0;
}
