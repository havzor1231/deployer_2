

import requests
from enum import Enum
from emora_stdm import DialogueFlow, Macro, Ngrams
from typing import Dict, Any, List
from json import JSONDecodeError
import json
import pickle
import re
import os
from src.utils.utils import MacroGPTJSON, MacroNLG, gpt_completion
from src.utils import utils
import openai


team_dict = json.load(open('resources/json/team_to_id_lower.json'))
home_vars = {}

class V(Enum):
    key_observations1 = 0  # str
    key_observations2 = 1  # str
    key_observations3 = 2  # str
    team1 = 3
    team2 = 4
    date = 5
    interested = 6


class MacroExplainStat(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        stats = vars["KEY_STATS"]
        stat_of_interest = vars["STAT_OF_INTEREST"]
        team1 = vars["TEAM1"]
        team2 = vars["TEAM2"]

        list_stats = stats.split("\n")
        stats_of_interest = ["score", "goals", "possession", "shots", "corners", "yellow cards", "red cards"]

        for i, curr in enumerate(stats_of_interest):
            if curr == stat_of_interest:
                curr_stat = list_stats[i]

                prompt = f'Explain the following football statistic in concise detail: {curr_stat}'
                output = gpt_completion(prompt)

        # print(list_stats, stat_of_interest)
        return output

def get_observations_prompt(vars: Dict[str, Any]):
    team1 = vars[V.team1.name]
    team2 = vars[V.team2.name]
    date = vars[V.date.name]

    prompt = "Get the key events of the English Premier League game between {} and {} on {}.".format(team1, team2, date)
    # print(prompt)
    return prompt

def get_key_observations(vars: Dict[str, Any]):
    observations1 = vars[V.key_observations1.name]
    observations2 = vars[V.key_observations2.name]
    observations3 = vars[V.key_observations3.name]

    return f"{observations1}\n{observations2}\n{observations3}"


class MacroGetName(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        r = re.compile(r"(?:\s|^)([a-z]+)$")
        m = r.search(ngrams.text())

        if m is None: return False

        firstname = None

        if m.group(1):
            firstname = m.group(1)

        vars['FIRSTNAME'] = firstname

        return True


class MacroUserVisited(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[str]):
        # print('macro user visited entered')
        firstname = vars['FIRSTNAME']
        return not vars.get(firstname, False)

class MacroStoreVisit(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[str]):
        firstname = vars['FIRSTNAME']
        if not vars.get(firstname):
            vars[firstname] = {}
            # print('stored new visitor')
        else:
            # print("visitor already seen")
        # print(vars)
        return True

def get_match(vars: Dict[str, Any]):
    team1 = vars[V.team1.name]
    team2 = vars[V.team2.name]
    date = vars[V.date.name]

    # print(team1, team2, date)
    if not team_dict.get(team1.lower()) or not team_dict.get(team2.lower()):
        print("one of two teams not found in dict.")
        # return False

    response = utils.get_key_stats(team1.lower(), team2.lower(), date)
    # print(response)

    vars["TEAM1"] = team1
    vars["TEAM2"] = team2
    vars["DATE"] = date

    vars["CURR_GAME_STATS"] = response

    return True



class MacroVisits(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        vn = 'VISITS'

        if vn not in vars:
            vars[vn] = 1
            return 'Quick pop quiz. What is Newcastle\'s nickname?'
        else:
            count = vars[vn] + 1
            vars[vn] = count
            match count:
                case 2: return 'What do you want to talk about?'
                case 3: return 'What brings you here today?'
                case default:
                    return 'What do you want to talk about?'

class MacroSetKeyStatFavPlayer(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        fav_player = vars["USER_FAV_PLAYER"]
        team1 = vars["TEAM1"]
        team2 = vars["TEAM2"]
        date = vars["DATE"]

        full_ex = {"TEAM1": "Manchester United", "TEAM2": "Newcastle", "DATE": "2022-03-04",
                  "KEY_STATS_FAV_PLAYER": "Final score Nottingham Forest 1 - 2 Liverpool \n "
                               "Goals: Nottingham Forest: Lewis Grabban (penalty, 59') Liverpool: Sadio Mane (19'), Mohamed Salah (75') \n "
                               "Possession: Nottingham Forest 35% - 65% Liverpool \n"
                               "Shots (on target): Nottingham Forest 7 (2) - 16 (5) Liverpool\n"
                               "Corners: Nottingham Forest 4 - 8 Liverpool \n"
                               "Yellow cards: Nottingham Forest 2 - 1 Liverpool \n"
                               "Red cards: None"}

        prompt = f'{fav_player} played his most recent game in {team1} vs. {team2} on {date}. ' \
                 f'Get the final score and key statistics of the game.' \
                 f'Respond in the JSON schema {full_ex}'

        output = gpt_completion(prompt)
        output = output.replace("{", "")
        output = output.replace("}", "")

        list_output = output.split(",")

        # print(type(output), output)
        d = json.loads(output)

        vars["TEAM1"] = d['TEAM1']
        vars["TEAM2"] = d['TEAM2']
        vars["DATE"] = d['DATE']
        vars["KEY_STATS_FAV_PLAYER"] = d['KEY_STATS_FAV_PLAYER']
        return True


class MacroSetKeyObsFavPlayer(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        fav_player = vars["USER_FAV_PLAYER"]
        team1 = vars["TEAM1"]
        team2 = vars["TEAM2"]
        date = vars["DATE"]

        full_ex = {"TEAM1": "Manchester United", "TEAM2": "Newcastle", "DATE": "2022-03-04",
                   "FINAL_SCORE": "This is the game Manchester United won 2-1.",
                   "KEY_OBS_RECENT_1": "Marcus Rashford scored the most crucial goal of the game.",
                   "KEY_OBS_RECENT_2": "Casemiro scored the first goal, which set the pace of the game.",
                   "KEY_OBS_RECENT_3": "Casemiro was assisted by Shaw to score the goal."
                   }

        empty_ex = {"TEAM1": "", "TEAM2": "", "DATE": "",
                   "FINAL_SCORE": "",
                   "KEY_OBS_RECENT_1": "",
                   "KEY_OBS_RECENT_2": "",
                   "KEY_OBS_RECENT_3": ""
                    }

        examples = f'{full_ex} or {empty_ex} if unavailable' if empty_ex else full_ex
        prompt = f'The soccer player {fav_player} played his most recent game in {team1} vs. {team2} on {date}. ' \
                 f'Get the final score and get the three most important moments of the stated match.' \
                 f'Respond in the JSON schema {examples}: {ngrams.raw_text().strip()}'

        output = gpt_completion(prompt)

        output = output.replace("'", '"')
        # print(output, type(output))

        new_output = ""
        for i, char in enumerate(output):
            if char == '"' and i < len(output) - 1 and output[i+1] == 's':
                new_output += "'"
            else:
                new_output += char

        # print(new_output)


        d = json.loads(new_output)
        # print(d)
        pass


#UNFAMILIAR MACROS
class MacroGetInterested(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        interested = vars[V.interested.name][0]
        if interested == 'true':
            vars['INTERESTED'] = 'true'
            # print('true')
        else:
            vars['INTERESTED'] = 'false'
            # print('false')


macros = {
    'VISITS': MacroVisits(),
    'SET_MATCH': MacroGPTJSON("What soccer match from the Premier League is the user interested in? If the two teams or date is not included, return False.",
                            {V.team1.name: "Manchester United", V.team2.name: "Newcastle", V.date.name: "2022-03-04"},
                            {V.team1.name: "Nottingham Forest", V.team2.name: "Liverpool", V.date.name: "2022-01-31"}
                            ),
    'GET_MATCH': MacroNLG(get_match),
    'GET_NAME': MacroGetName(),
    'VISITED_BEFORE': MacroUserVisited(),
    'STORE_VISIT': MacroStoreVisit(),
    'EXPLAIN_STAT': MacroExplainStat(),
    'SET_KEY_STATISTICS': MacroGPTJSON("What soccer match from the Premier League is the user interested in? Get the key statistics of the stated match.",
                                         {"TEAM1": "Manchester United", "TEAM2": "Newcastle", "DATE": "2022-03-04",
                                          "KEY_STATS": "Final score: Nottingham Forest 1 - 2 Liverpool \n "
                                                       "Goals: Nottingham Forest: Lewis Grabban (penalty, 59') Liverpool: Sadio Mane (19'), Mohamed Salah (75') \n "
                                                       "Possession: Nottingham Forest 35% - 65% Liverpool \n"
                                                       "Shots (on target): Nottingham Forest 7 (2) - 16 (5) Liverpool\n"
                                                       "Corners: Nottingham Forest 4 - 8 Liverpool \n"
                                                       "Yellow cards: Nottingham Forest 2 - 1 Liverpool \n"
                                                       "Red cards: None"}),
    'SET_KEY_OBSERVATIONS': MacroGPTJSON("What soccer match from the Premier League is the user interested in? Get the three most important moments of the stated match.",
                                         {V.team1.name: "Manchester United", V.team2.name: "Newcastle", V.date.name: "2022-03-04",
                                          V.key_observations1.name: "Marcus Rashford scored the most crucial goal of the game.",
                                          V.key_observations2.name: "Casemiro scored the first goal, which set the pace of the game.",
                                          V.key_observations3.name: "Casemiro was assisted by Shaw to score the goal."}),
    'GET_KEY_OBSERVATIONS': MacroNLG(get_key_observations),
    'SET_FAV_TEAM': MacroGPTJSON("What is the user's favorite Premier League team? "
                                  "Give three biased reasons why Manchester City is superior than the user's favorite team. "
                                  "If their favorite team is different, be condescending.",
                                  {'USER_FAV_TEAM': "Arsenal",
                                   'REASON1': "They have strong attacking plays that are fun to watch.",
                                   'REASON2': "They always have the mindset of a champion and win important matches.",
                                   'REASON3': "Especially when they have a lead, the defense is stellar."}),
    'SET_FAV_PLAYER': MacroGPTJSON("Who is the speaker's favorite soccer player? Give the most recent Premier League game the player has played in.",
                                  {'USER_FAV_PLAYER': "Marcus Rashford",
                                   'DATE': "2022-03-04",
                                   'TEAM1': "Manchester United",
                                   'TEAM2': "Tottenham"}),
    'SET_KEY_OBS_FAV_PLAYER': MacroGPTJSON("Who is the speaker's favorite soccer player? Get the most recent game the favorite player has played in the Premier League. Give the key observations of the game and get the final score.",
                                  {'USER_FAV_PLAYER': "Marcus Rashford",
                                   'FINAL_SCORE': "This is the game where Manchester United won 3-1.",
                                   "KEY_OBS_1": "Marcus Rashford scored the most crucial goal of the game.",
                                   "KEY_OBS_2": "Casemiro scored the first goal, which set the pace of the game.",
                                   "KEY_OBS_3": "Casemiro was assisted by Shaw to score the goal."
                                   }),
    'SET_TEAM_KEY_PLAYERS': MacroGPTJSON("What team is the user interested in? Who are the top two key players on the team currently, and why? Who is the top player of all time on the team historically, and why? Give a passionate answer.",
                                        {'TOP_TEAM': "Tottenham Hotspurs",
                                         'KEY_PLAYER_1': "Harry Kane is the most crucial forward because he converts the shots in goals.",
                                         'KEY_PLAYER_2': "With strong command of his penalty area and the goal line, Hugo Lloris  kept 34 clean sheets in 100+ Premier League games.",
                                         'GOAT_PLAYER': 'Gareth Bale is one the most impressive forwards of our generation, and his acrobatic kick against Stoke City in 2010 was legendary.'}
),
    'SET_TEAM_KEY_MANAGER': MacroGPTJSON("What team is the user interested in? What are two key management decisions that resulted in a significant increase in wins for the team?",
                                        {'TOP_TEAM': "Tottenham Hotspurs",
                                         'KEY_DECISION_1': "Hiring Mauricio Pochettino: In 2014, Tottenham Hotspur hired Mauricio Pochettino as their manager. Pochettino brought a new style of play to the team, focusing on high-pressing and quick transitions. He also implemented a strong team culture, with a focus on hard work, discipline, and teamwork. Under Pochettino's leadership, Tottenham Hotspur achieved their highest-ever Premier League finish in the 2015-16 season, finishing third and qualifying for the Champions League.",
                                         'KEY_DECISION_2': "Signing key players: Tottenham Hotspur has also made several key signings in recent years that have contributed to their success on the pitch. One notable example is the signing of Harry Kane, a prolific striker who has been instrumental in the team's attack. Other important signings include Dele Alli, Christian Eriksen, and Son Heung-min, who have all played key roles in the team's success."}),

    #UNFAMILIAR MACROS
    'SET_INTERESTED': MacroGPTJSON('Do you think the user is interested in knowing more?',
        {V.interested.name: ["true", "false"]}
    ),
    'GET_INTERESTED': MacroGetInterested()
}

def start_transition() -> DialogueFlow:
    transitions = {
        'state': 'start',
        '`Welcome! I am dEPLoyer, English Premier League Chatbot. What\'s your name?`': {
            '#GET_NAME' : {
                # If previous visitor, direct to familiar state.
                # Else, give pop quiz and cache current visit.
                '#IF(#VISITED_BEFORE)` Welcome back.`' : 'new_familiar',
                '`Nice to meet you. `#STORE_VISIT': 'pop_quiz'
            }
        }
    }

    df = DialogueFlow('start', end_state='end')
    df.load_transitions(transitions)
    df.load_transitions(new_familiar)
    df.load_transitions(pop_quiz_transition)
    df.load_transitions(key_statistics_state)
    df.load_transitions(continue_conversation_state)
    df.load_transitions(continue_explain_stats_state)
    df.load_transitions(continue_explain_stats_state2)
    df.load_transitions(key_observations_state)
    df.load_transitions(favorite_team_state)
    df.load_transitions(team_key_managers_state)
    df.load_transitions(favorite_player_state)
    df.load_transitions(team_key_players_state)
    df.load_transitions(team_state)
    df.add_macros(macros)

    #UNFAMILIAR DIALOGUE
    df.load_transitions(unfamiliar)
    df.load_transitions(player_recommendation)
    df.load_transitions(rashford_rec)
    df.load_transitions(kane_rec)
    df.load_transitions(de_bruyne_rec)
    df.load_transitions(kante_rec)
    df.load_transitions(personal_story)
    df.load_transitions(team_recommendation)
    df.load_transitions(fun_fact)

    return df

pop_quiz_transition = {
    'state': 'pop_quiz',
    '`Quick pop quiz. What team is Harry Kane on currently?`' : {
        '[{tottenham, hotspur, spur, hotspurs, spurs, lilywhites}]': {
            '`Yep! What team is Mohamed Salah playing for currently?`': {
                '[{liverpool, liverpool fc, liverpool f.c., the reds}]': {
                    '`Wow! You must have some knowledge in soccer. Let\'s get started!`': 'new_familiar'
                },
                'error': {
                    '`Oops, you got that wrong. That\'s fine, not everyone is into football.`' : 'unfamiliar'
                }
            }
        },
        'error': {
            '`Oops, you got that wrong. That\'s fine, not everyone is into football.`' : 'unfamiliar'
        }
    }
}

continue_conversation_state = {
    'state': 'cont_convo',
    '`Do you want to continue the conversation?`': {
        '[{yes, sure, yeah, yea, okay, ok}]': 'new_familiar',
        '[{no, nope, nah}]': {
            '`Okay, hope you enjoyed!`': 'end' #TODO: add evaluation state
        },
        'error': {
            '`I don\'t understand you.`': 'end'
        }
    }
}

continue_explain_stats_state = {
    'state': 'continue_explain',
    '`Do you want me to explain anything else?`': {
        '[$STAT_OF_INTEREST={score, goals, possession, shots, corners, yellow cards, red cards, possession}]': {
            '` `#EXPLAIN_STAT` \n`': 'continue_explain'
        },
        '[{no, nope, nah}]': {
            '`That\'s fine. Do you want to talk about the key observations that resulted in the win?`': {
                '[{yes, sure, yeah, yea, okay, ok}]': {
                    '` `#GET_KEY_OBSERVATIONS` \n`': 'cont_convo'
                },
                '[{no, nope, nah}]': {
                    '`Okay, hope you enjoyed!`': 'end'  # TODO: add evaluation state
                },
                'error': {
                    '`Sorry, I didn\'t understand you.`': 'end'
                }
            }
        },
        'error': {
                    '`I don\'t know about that statistic.`': 'end'
        }
    }
}

continue_explain_stats_state2 = {
    'state': 'continue_explain2',
    '`Do you want me to explain anything else?`': {
        '[$STAT_OF_INTEREST={score, goals, possession, shots, corners, yellow cards, red cards, possession}]': {
            '` `#EXPLAIN_STAT` \n`': 'continue_explain2'
        },
        '[{no, nope, nah}]': 'cont_convo',
        'error': {
                    '`I don\'t know about that statistic.`': 'end'
        }
    }
}

key_statistics_state = {
    'state': 'key_stats',
    '`Sure, I can help you with that. What match do you want to talk about?`': {
        '#SET_KEY_STATISTICS #SET_KEY_OBSERVATIONS': {
            '` Here are the key statistics: \n`$KEY_STATS`\n Do you want me to explain any of these?`': {
                '[$STAT_OF_INTEREST={score, goals, possession, shots, corners, yellow cards, red cards, possession}]': {
                    '` `#EXPLAIN_STAT` \n`': 'continue_explain'
                },
                '[{no, nope, nah}]': {
                    '`That\'s fine. Do you want to talk about the key observations that resulted in the win?`': {
                        '[{yes, sure, yeah, yea, okay, ok}]': {
                            '` `#GET_KEY_OBSERVATIONS` \n`': 'cont_convo'
                        },
                        '[{no, nope, nah}]': {
                            '`Okay, hope you enjoyed!`': 'end'  # TODO: add evaluation state
                        },
                        'error': {
                            '`Sorry, I didn\'t understand you.`': 'end'
                        }
                    }
                },
                'error': {
                    '`I don\'t know about that statistic.`': 'end'
                }

            }
        }
    }
}

key_observations_state = {
    'state': 'key_observations',
    '`Sure, I can help you with that. What match do you want to talk about?`': {
        '#SET_KEY_OBSERVATIONS #SET_KEY_STATISTICS' : {
            '` Here are the key observations: `#GET_KEY_OBSERVATIONS` \n'
            'Do you want to talk about the key statistics of the game?`': {
                '[{yes, sure, yeah, yea, okay, ok}]': {
                    '` Here are the key statistics: \n`$KEY_STATS`\n Do you want me to explain any of these?`': {
                        # explain the requested statistic
                        '[$STAT_OF_INTEREST={score, goals, possession, shots, corners, yellow cards, red cards, possession}]': {
                            '` `#EXPLAIN_STAT` \n`': 'continue_explain2'
                        },
                        # if not interested, ask if user wants to continue conversation
                        '[{no, nope, nah}]': 'cont_convo',
                        'error': {
                            '`I don\'t know about that statistic.`': 'end'
                        }
                    }
                },
                '[{no, nope, nah}]': {
                    '`Okay, hope you enjoyed!`': 'end'  # TODO: add evaluation state
                },
                'error': {
                    '`Sorry, I didn\'t understand you.`': 'end'
                }
            }
        }
    }
}



favorite_team_state = {
    'state': 'favorite_team',
    '`My favorite team is Manchester City. What\'s yours?`': {
        '#SET_FAV_TEAM' : {
            '` Man City will always be my team. `$REASON1`\n`$REASON2`\n`$REASON3` '
            'Do you want to talk`about `$USER_FAV_TEAM`\'s specific match or team?' : {
                '[match]': {
                    '`For matches, I can talk about key statistics or key observations. What do you want to talk about?`': {
                        '[{statistics, statistic}]': 'key_stats',
                        '[{observation, observations}]': 'key_observations',
                        'error': {
                            '`I don\'t understand!`': 'end'
                        }
                    }
                },
                '[favorite, player]': 'favorite_player',
                '[!-favorite, team]': 'team_state',
                'error': 'end'
            }
        },
        'error': {
            '`I do not recognize that team.`': 'end'
        }
    }
}

favorite_player_state = {
    'state': 'favorite_player',
    '`My favorite player is Ronaldo, the greatest football player alive. Who\'s yours?`': {
        '#SET_FAV_PLAYER #SET_KEY_OBS_FAV_PLAYER' : {
            '` I watched `$USER_FAV_PLAYER` in his most recent game between `$TEAM1` and `$TEAM2`. \nThere\'s some cool'
            ' moments in that game. \nActually, do you wanna know some key observations I made about the game?`' : {
                '[{yes, sure, yeah, yea, okay, ok}]': {
                    '` `$FINAL_SCORE` \n`$KEY_OBS_1` \n`$KEY_OBS_2` \n`$KEY_OBS_3` \n`': 'cont_convo'
                },
                '[{no, nope, nah}]': 'cont_convo',
                'error': {
                    '`Sorry, I do not understand you.`': 'end'
                }
            }
        },
        'error': {
            'I do not recognize that player.': 'end'
        }
    }
}

team_key_players_state = {
    'state': 'team_key_players',
    '`Sure, I can do that for you. Which team do you wanna talk about?`': {
        '#SET_TEAM_KEY_PLAYERS #SET_TEAM_KEY_MANAGER' : {
            '` Here\'s my take on `$TOP_TEAM` \'s players. \n`$KEY_PLAYER_1` \nAlso, `$KEY_PLAYER_2` \nBut `$GOAT_PLAYER`\n'
            'Did you want to talk about the key management plays?`': {
                '[{yes, sure, yeah, yea, okay, ok}]': {
                    '` Here\'s my take on `$TOP_TEAM`\'s management decisions. \n`$KEY_DECISION_1` \n`$KEY_DECISION_2`\n`': 'cont_convo'
                },
                '[{no, nope, nah}]': 'cont_convo',
                'error': {
                    '`Sorry, I didn\'t understand you.`': 'end'
                }
            }
        }
    }
}

team_key_managers_state = {
    'state': 'team_key_managers',
    '`Sure, I can do that for you. Which team do you wanna talk about?`': {
        '#SET_TEAM_KEY_MANAGER #SET_TEAM_KEY_PLAYERS': {
            '` Here\'s my take on `$TOP_TEAM`\'s management decisions. \n`$KEY_DECISION_1` \n`$KEY_DECISION_2`\n'
            'Did you want to talk about the key players on the team? `': {
                '[{yes, sure, yeah, yea, okay, ok}]': {
                    '` Here\'s my take on `$TOP_TEAM` \'s players. \n`$KEY_PLAYER_1` \nAlso, `$KEY_PLAYER_2` \nBut `$GOAT_PLAYER`\n`': 'cont_convo'
                },
                '[{no, nope, nah}]': 'cont_convo',
                'error': {
                    '`Sorry, I didn\'t understand you.`': 'end'
                }
            }
        }
    }
}

team_state = {
    'state': 'team_state',
    '`For teams, I can talk about the key players or the organizational decisions made by the managers. What do you want to talk about?`': {
        '[{player, players}]': 'team_key_players',
        '[{manager, managers, decisions, organizational}]': 'team_key_managers',
        'error': {
            '`I can talk about players or managers!`': 'end'
        }
    }
}

new_familiar = {
    'state': 'new_familiar',
    '`I can talk about a specific match or team. '
    'What are you interested in talking about?`': {
        '[match]': {
            '`For matches, I can talk about key statistics or key observations. What do you want to talk about?`': {
                '[{statistics, statistic}]': 'key_stats',
                '[{observation, observations}]': 'key_observations',
                'error': {
                    '`I don\'t understand!`': 'end'
                }
            }
        },
        '[favorite, team]' : 'favorite_team',
        '[favorite, player]': 'favorite_player',
        '[!-favorite, team]': 'team_state',
        'error': 'end'
    }
}

# UNFAMILIAR DIALOGUE

unfamiliar = {
    'state': 'unfamiliar',
    '`Manchester United is part of EPL.  The Premier League was founded in 1992, '
    'replacing the First Division as the top tier of English football. Does this sound interesting to you?`': {
        '[yes]': {
            '`Great! Let\'s start with one of the most successful teams in the EPL historically! Manchester United is one of the most successful teams in the English Premier League. The famous player '
            'Cristiano Ronaldo was once a member of Manchester United!`': {
                '#SET_INTERESTED #GET_INTERESTED': {
                    '#IF($INTERESTED=true) `Manchester United can be one of my favorite teams. Do you have any favorite team in EPL so far?`': {
                        '[yes]': {
                            '`Good for you! `': 'match_discussion'
                        },
                        'error': {
                            '`Oh that\'s fine. I watched Manchester United\'s recent game with Sevilla, another team in EPL. It was so intense! They got 2-2 eventually.`': {
                                '#SET_INTERESTED #GET_INTERESTED': {
                                    '#IF($INTERESTED=true) `I know! Sabitzer from Manchester United had the first goal 14 minutes after the game for his team! '
                                    'That is such a quick goal! Given that the average first goal for soccer game is after 30 minutes on average!`': {
                                        '#SET_INTERESTED #GET_INTERESTED': {
                                            '#IF($INTERESTED=true)`Manchester United’s squad is one of the biggest in the Premier League and it’s filled up with quality players in every position. '
                                            'They are actually gonna have a game with Tottenham Hotspur soon.'
                                            'They have long been rivals with each other and Hotspur currently ranks one below Manchester United!'
                                            'Do you bother betting on their results?`': {
                                                '#UNX': {
                                                    '` I would say 2-0. It somehow made me recall their game last '
                                                    'year in October. They had 0-0 at half time.`':
                                                        'player_recommendation'
                                                },
                                            }
                                        },
                                             '#IF($INTERESTED=false)': 'fun_fact'
                                    },
                                        '#IF($INTERESTED=false)': 'fun_fact'
                                }
                            }
                        },

                    },
                        '#IF($INTERESTED=false)': 'fun_fact'
                },
                '#IF($INTERESTED=false)': 'fun_fact'
            }
        }
    },
    '`[no]`': 'player_recommendation'

}

player_recommendation = {
    'state': 'player_recommendation',
    '#GATE `Do you want to know more about some players? Marcus Rashford is my favorite from Manchester United. Well, if you\'re looking for a football player who can run faster than a cheetah on Red Bull, score goals like it\'s his job (oh wait,'
    'it actually is his job), and make the opposing team\'s defense look like a bunch of lost toddlers, then Marcus Rashford is your man. `': 'rashford_rec',
    '#GATE `Do you want to know more about some players? Harry Kane is my favorite from Tottenham Hotspur. He is not '
    'just a goal-scoring machine, he\'s also a great team player.'
    ' He has a knack for creating chances for his teammates and can change the course of a game with his passing and playmaking abilities.`': 'kane_rec',
    '#GATE `Do you want to know more about some players? Kevin De Bruyne is my favorite Manchester City player. If you love players who can play any offensive role'
    'and passes beautifully, you would love De Bruyne!`': 'de_bruyne_rec',
    '#GATE `Do you want to know more about some players? Kante is my favorite Chelsea player. He\'s one of the most hard playing players I have ever seen.'
    'he always runs non-stop to take back possession from the opponent and he\'s very good at it too! What he is also good at is passing the ball and linking it with his fellow teammates'
    'Overall, he\'s a wonderful team player and a truly devoted player!`': 'kante_rec'
}

rashford_rec = {
    'state': 'rashford_rec',
    '`In fact, if football was a video game, Marcus would be the cheat code that everyone wants to unlock. `': {
        '#SET_INTERESTED #GET_INTERESTED': {
            '#IF($INTERESTED=true)`Rashford appeared 233 times in this season and had 74 goals. He is absolutely one of the heated players. Do you want to look at some of his game stats?`':{
                '[yes]': {
                    '`stats Speaking of this, I am a big fan of Manchester United as well. Do you think you would like Manchester United? Manchester United is a team with a rich history and a tradition of excellence.'
                    'If you want to support a team that has consistently been among the best in the world, then Manchester United is a great choice.`': {
                        '[yes]': {
                            '`You know what, they are gonna meet their long-time enemy team Chelsea! The rivalry between Manchester United'
                            'and Chelsea is one of the most intense in English football, and every game between these two teams is a must-watch for fans. They were 1-1 last time! How intense!'
                            ' What do you think will be the score this time?`': {
                                '#UNX': {
                                    '`I would say Manchester United 2 and Chelsea 1. People are accusing of Chelsea being bad at coopertion these days. So who knows haha!`': 'personal_story'
                                }
                            }
                        },
                        '[no]': 'team_recommendation'
                    }
                },
                '[no]': 'player_recommendation'
            },
            '#IF($INTERESTED=false)': 'personal_story'
        }
    }
}

kane_rec = {
    'state': 'kane_rec',
    '`Despite his success on the field, Harry Kane remains humble and grounded.`': {
        '#SET_INTERESTED #GET_INTERESTED': {
            '#IF($INTERESTED=true) `Harry Kane appeared 313 times and had 206 goals. You can call him one of the most successful commissioned players. Do you want to know how he performed?`': {
                    '[yes]': {
                        '`stats Tottenham Hotspur is viral these days! Some of their players made wonderful performance at the World Cup.'
                        'I personally like this team a lot! Do you think you would like it?`': {
                            '[yes]': {
                                '`Great haha another Hotspur fan! Their next game is with team New Castle. I somehow think that New Castle has a decent ranking (they exceeds Hotspur sometime these days!) because they made lots of draws.'
                                'Last time when they met, New Castle had 2 and Tottenham Hotspur had 1. What do you think will be their next score?`': {
                                    '#UNX': {
                                        '`I would just say they will have another draw. From my perspective, New Castle is known for fast-paced games but Tottenham Hotspur'
                                        'plays possession-based games and has won two league titles. Who knows haha!`': 'personal_story'
                                    },
                                }
                            },
                            '[no]': 'team_recommendation'
                        }
                    },
                    '[no]': 'player_recommendation'
                },
            '#IF($INTERESTED=false)': 'personal_story'
            },

        }
    }


de_bruyne_rec = {
    'state': 'de_bruyne_rec',
    '`He is such an outstanding player!`': {
        '#SET_INTERESTED #GET_INTERESTED': {
            '#IF($INTERESTED=true)`De Bruyne appeared almost 240 times in the premier league and had 101 assists! He created 160 big chances for his teamates. Truly, he is on top of his league. Do you want to know more about how he performed?`': {
                    '[yes]': {
                        '`stats Manchester City is truly one of the strongest team in all of Europe! However, even this team is impacted by whether De Bruyne is playing or not.'
                        'In other words, he is the focal point of the playstyle of Manchester City that highlights possession which requires good passing. I like the style of Manchester City a lot! Do you think you would like this team?`': {
                            '[yes]': {
                                '`Good choice for you since Manchester City really made the history of English Premier League and as I recalled, they rank at the second place.'
                                ' Their next game is with Arsenal and dude! That\'s gonna be such a tough game since Arsenal currenly rank the first. And let me tell you, I don\'t buy it. Anyways, Arsenal did win 13 league titles.'
                                'It\'s gonna be very hard for Manchester City but I count on their quick and incisive passing to break down opposition defenses. What do you think, who between them will win?`': {
                                    '#UNX': {
                                        '`Though as a big fan of Manchester City, Arsenal has indeed been the top one for a while. Maybe Mamchester City will lose this time.`': 'personal_story'
                                    }
                                }
                            },
                            '[no]': 'team_recommendation'
                        }
                    },
                    '[no]': 'player_recommendation'
                },
                '#IF($INTERESTED=false)': 'personal_story'
            },
        }
    }


kante_rec = {
    'state': 'kante_rec',
    '`He is a star!`': {
        '#SET_INTERESTED #GET_INTERESTED': {
            '#IF($INTERESTED=true) `Kante appeared around 230 games in the premier league. He made a staggering 505 interceptions and 1685 recoveries, which means he did astonishingly well in recovering the ball! Do you want to know more about how he performed?`': {
                    '[yes]': {
                        '`stats Chelsea historically has a very strong performance! Although Kante is not the type of player that gets the spotlight, Chelsea holds differently whenever Kante is playing for them'
                        'When he plays, there\'s always a stability to Chelsea that makes them look very hard to beat! Chelsea is known for its passionate fans and iconic blue jerseys. Do you think you will like Chelsea?`': {
                            '[yes]': {
                                '`Yay! Chelsea\'s next game is with Bretford. Surprisingly, during their recent games, Chelsea had exactly one wining, one loss, and one draw.'
                                'Chelsea\'s manager Thomas Tuchel really knows how to operate the teams and led the team to their recent success. But Bretford is known for using good data analytics. Who do you think will win?`': {
                                    '#UNX': {
                                        '`I would say, let\'s see, that Bretford would win. I recalled that Bretford won 4-1 to Chelsea, just last year in April. Uhh, bad memory. Anyways.`': 'personal_story'
                                    },
                                }
                            },
                            '[no]': 'team_recommendation'
                        }
                    },
                    '[no]': 'player_recommendation'
                },
            '#IF($INTERESTED=false)': 'personal_story'
            },
        }
    }

personal_story = {
    'state': 'personal_story',
    '#GATE`You know I remember I never wanted to do any exercise before I watched EPL. After watching that I found it really cool to just run freely on the field and even sweating makes me feel happy!`':{
        '/.*/':{
            '`Haha, you know how people say soccer really cheers people up. That is exactly what I feel. Speaking of that, i want to share this video with you. I really feel the same.`':'video'
        }
    },
    '#GATE `I once had a big fight with my dad because he really thought Arsenal would win but I thought Manchester City would win the champion. I mean I got it right. But we ended up just having a wonderful time watching the final together with beer and barbecue! It was such a wonderful time!':'fun_fact'
}

team_recommendation = {
    'state': 'team_recommendation',
    '#GATE `Do you want to hear about the teams in Premier League then? `': 'end'
}
fun_fact={
    'state':'fun_fact',
    '`fun facts`':'end'
}


def save(df: DialogueFlow, varfile: str):
    df.run()
    d = {k: v for k, v in df.vars().items() if not k.startswith('_')}
    pickle.dump(d, open(varfile, 'wb'))

def load(df: DialogueFlow, varfile: str):
    if os.path.exists(varfile):
        d = pickle.load(open(varfile, 'rb'))
        df.vars().update(d)
    openai.api_key_path = utils.OPENAI_API_KEY_PATH
    df.run()
    save(df, varfile)

load(start_transition(), 'resources/visits.pkl')
