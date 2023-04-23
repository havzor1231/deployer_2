import requests
from enum import Enum
from emora_stdm import DialogueFlow
from emora_stdm import Macro, Ngrams
from typing import Dict, Any, List
import openai
from typing import Dict, Any, List
import re
import os


team_dict = {
    'arsenal': 'Arsenal',
    'aston villa': 'Aston Villa',
    'brentford': 'Brentford',
    'brighton': 'Brighton & Hove Albion',
    'burnley': 'Burnley',
    'chelsea': 'Chelsea',
    'crystal palace': 'Crystal Palace',
    'everton': 'Everton',
    'leeds united': 'Leeds United',
    'leicester city': 'Leicester City',
    'liverpool': 'Liverpool',
    'manchester city': 'Manchester City',
    'manchester united': 'Manchester United',
    'newcastle united': 'Newcastle United',
    'norwich city': 'Norwich City',
    'southampton': 'Southampton',
    'tottenham': 'Tottenham Hotspur',
    'watford': 'Watford',
    'west ham united': 'West Ham United',
    'wolverhampton': 'Wolverhampton Wanderers'
}

class MacroHome(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        user_input = input().lower()
        if user_input in team_dict:
            team_name = team_dict[user_input]
            # make team_name into team id
            url = "https://sofascores.p.rapidapi.com/v1/teams/rankings"
            querystring = {"name": team_name}
            headers = {
                "X-RapidAPI-Key": "dbad2f5186msh2f81b29abdc6d29p17a232jsndd11cefd33a8",
                "X-RapidAPI-Host": "sofascores.p.rapidapi.com"
            }
            response = requests.request("GET", url, headers=headers, params=querystring)
            data = response.json()['data']
            ranking = data[0]['ranking']
            year = data[0]['year']
            vars['home_team_ranking'] = ranking
            # [team name] ranked [rank] in [2021]
            print(team_name + " is ranked #" + str(ranking) + " in " + str(year))
        else:
            print('That team is not part of EPL')


transitions = {
        'state': 'start',
        '`Hi, I am dEPLoyer! Have you ever heard of Manchester United? `': {
            '[yes]': 'familiar',
            'error': 'fun_fact'
        },
    }

familiar = {
        'state': 'familiar',
        '`Do you watch EPL in your free time?`': {
            '[yes]': {
                '`I do too! Do you have a favorite team?`': {
                    '#GET_HOME_TEAM': 'end'
                    },
                    '[no]': {
                        '`okay`': 'end'
                    },
                }
            },

            '[no]': {
                '`Why do you not watch it?`': {
                    '[not interested]': {
                        '`I love EPL for xxxxxxx, does this interest you?` ': {
                            '[yes]': 'end'
                        }
                    },
                    '[dont know]': 'introducing EPL'
                }
            },
        }

macros = {
        'GET_HOME_TEAM': MacroHome()
    }



df = DialogueFlow('start', end_state='end')
df.load_transitions(transitions)
df.load_transitions(familiar)
df.add_macros(macros)

if __name__ == '__main__':
    df.run()
