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
            '[no]': 'unfamiliar',
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


unfamiliar={
    'state':'unfamiliar',
    '`Manchester United is part of EPL.  The Premier League was founded in 1992, '
    'replacing the First Division as the top tier of English football. Does this sound interesting to you?`':{
        '[yes]':{
            '`Great! Manchester United is one of the most successful teams in the English Premier League. The famous player'
            'Cristiano Ronaldo was once a member of Manchester United!`':{
                '#GET_INTERESTED':{
                    '$IF_Interested `Manchester United can be one of my favorite team. Do you have any favorite team in EPL so far?`':{
                        '#GET_HOME_TEAM':{
                            '`Good for you! `$home_team_ranking`.`':'match_discussion'
                        },
                        'error':{
                        '`Oh that\'s fine. I watched Manchester United\'s recent game with Sevilla, another team in EPL. It was so intense! They got 2-2 eventually.`':{}
                                '#GET_INTERESTED':{
                                    '$IF_Interested `I know! Sabitzer from Manchester United had the first goal 14 minutes after the game for his team! '
                                    'That is such a quick goal! Given that the average first goal for soccer game is after 30 minutes on average!`':{
                                        '#GET_INTERESTED':{
                                            '$IF_Interested':{
                                                 '`Manchester United’s squad is one of the biggest in the Premier League and it’s filled up with quality players in every position. They are actually gonna have a game with Tottenham Hotspur soon.
                                                 'They have long been rivals with each other and Hotspur currently ranks one below Manchester United!
                                                 'Do you bother bet on their results?`':{
                                                     '/*':{
                                                         '#UNX, I would say 2-0. It somehow made me recall their game last year in October. They had 0-0 at half time.`':'end'
                                                     },
                                                 },
                                            },
                                            '$IF_NotInterested':'fun_fact'
                                        }

                                    }
                                    },
                                      '$IF_NotInterested':'fun_fact'
                           }
                        },
                    '$IF_NotInterested':'fun_fact'
                    }
                }
            }
        '`[no]`':'player_recommendation'

    }

}

player_recommendation={
    'state':'player_recommendation',
    '#GATE `Do you want to know more about some players? Marcus Rashford is my favorite from Manchester United. Well, if you\'re looking for a football player who can run faster than a cheetah on Red Bull, score goals like it\'s his job (oh wait,'
    'it actually is his job), and make the opposing team\'s defense look like a bunch of lost toddlers, then Marcus Rashford is your man. `':'rashford_rec',
    '#GATE `Do you want to know more about some players? Harry Kane is my favorite from Tottenham Hotspur. He is not just a goal-scoring machine, he\'s also a great team player.'
    ' He has a knack for creating chances for his teammates and can change the course of a game with his passing and playmaking abilities.`':'kane_rec',
}

rashford_rec={
    'state':'rashford_rec',
    '`In fact, if football was a video game, Marcus would be the cheat code that everyone wants to unlock. `':{
        '#GET_Interested':{
            '$IF_Interested':{
                '`Rashford appeared 233 times in this season and had 74 goals. He is absolutely one of the heated players. Do you want to look at some of his game stats?`:{'
                '[yes]':{
                    '`stats` Speaking of this, I am a big fan of Manchester United as well. Do you think you would like Manchester United? Manchester United is a team with a rich history and a tradition of excellence.'
                    'If you want to support a team that has consistently been among the best in the world, then Manchester United is a great choice.':{
                        '[yes]':{
                            '`cool`':'end'
                        },
                        '[no]':'team_recommendation'
                    }
                },
                '[no]':'player_recommendation'
            }
        }
    }
}
kane_rec={

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