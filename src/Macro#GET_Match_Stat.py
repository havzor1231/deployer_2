import requests

from enum import Enum
from emora_stdm import DialogueFlow
from emora_stdm import Macro, Ngrams
from typing import Dict, Any, List
import openai
from typing import Dict, Any, List
import re
import os


class MacroGetMatchStat(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        team_mentioned = []
        team1, team2 = None, None


        team_names= ["Arsenal", "Aston Villa", "Blackburn Rovers", "Chelsea", "Coventry City", "Crystal Palace", "Everton",
                      "Ipswich Town", "Leeds United",
                      "Liverpool", "Manchester City", "Manchester United", "Middlesbrough", "Norwich City",
                      "Nottingham Forest",
                      "Oldham Athletic", "Queens Park Rangers",
                      "Sheffield United", "Sheffield Wednesday", "Southampton", "Tottenham Hotspur", "Wimbledon"]

        for team in team_names:
            if team in ngrams.raw_text():
                team_mentioned.append(team)



        team1 = team_mentioned[0]
        team2 = team_mentioned[1]
# possibly remove everything below
        url = "https://heisenbug-premier-league-live-scores-v1.p.rapidapi.com/api/premierleague/match/events"

        querystring = {"team1": team1, "team2": team2}

        headers = {
                     "X-RapidAPI-Key": "73c83052efmshaa867d4a4f50068p1dde59jsn4703d6c45a54",
                     "X-RapidAPI-Host": "heisenbug-premier-league-live-scores-v1.p.rapidapi.com"
         }

        response = requests.request("GET", url, headers=headers, params=querystring)

        vars['RESPONSE'] = response.text
        print(response.text)



transitions = {
    'state': 'start',
    '`What do you want to talk about?`': {
        '#GET_Match_Stat':{
            '`$RESPONSE`':'end'
        }

    }
}


macros = {
        'GET_Match_Stat': MacroGetMatchStat()
    }

df = DialogueFlow('start', end_state='end')
df.load_transitions(transitions)
df.add_macros(macros)

if __name__ == '__main__':
    df.run()








