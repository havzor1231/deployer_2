import requests
from emora_stdm import Macro, Ngrams
from typing import Dict, Any, List, Callable, Pattern
import json
import re
from src.utils import regexutils
import openai
from json import JSONDecodeError


headers = {
    "X-RapidAPI-Key": "1b0a42ee93msh3c60044810c2171p15d22bjsn431cea4eea20",
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

team_dict = json.load(open('resources/json/team_to_id_lower.json'))

# GPT API CODE
OPENAI_API_KEY_PATH = 'utils/openai_api.txt'
CHATGPT_MODEL = 'gpt-3.5-turbo'


class MacroGPTJSON(Macro):
    def __init__(self, request: str, full_ex: Dict[str, Any], empty_ex: Dict[str, Any] = None, set_variables: Callable[[Dict[str, Any], Dict[str, Any]], None] = None):
        """
        :param request: the task to be requested regarding the user input (e.g., How does the speaker want to be called?).
        :param full_ex: the example output where all values are filled (e.g., {"call_names": ["Mike", "Michael"]}).
        :param empty_ex: the example output where all collections are empty (e.g., {"call_names": []}).
        :param set_variables: it is a function that takes the STDM variable dictionary and the JSON output dictionary and sets necessary variables.
        """
        self.request = request
        self.full_ex = json.dumps(full_ex)
        self.empty_ex = '' if empty_ex is None else json.dumps(empty_ex)
        self.check = re.compile(regexutils.generate(full_ex))
        self.set_variables = set_variables

    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        examples = f'{self.full_ex} or {self.empty_ex} if unavailable' if self.empty_ex else self.full_ex
        prompt = f'{self.request} Respond in the JSON schema such as {examples}: {ngrams.raw_text().strip()}'
        output = gpt_completion(prompt)
        if not output: return False
        # print(output)
        try:
            d = json.loads(output)
        except JSONDecodeError:
            print(f'Invalid: {output}')
            return False

        if self.set_variables:
            self.set_variables(vars, d)
        else:
            vars.update(d)

        return True


class MacroNLG(Macro):
    def __init__(self, generate: Callable[[Dict[str, Any]], str]):
        self.generate = generate

    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        return self.generate(vars)


def gpt_completion(input: str, regex: Pattern = None) -> str:
    # print(input)
    response = openai.ChatCompletion.create(
        model=CHATGPT_MODEL,
        messages=[{'role': 'user', 'content': input}]
    )
    output = response['choices'][0]['message']['content'].strip()
    # print(output)

    if regex is not None:
        m = regex.search(output)
        output = m.group().strip() if m else None

    return output


# MACRO HELPER FUNCTIONS
def get_key_observations(team1, team2, month, day, year):
    # get fixture id of mentioned match
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/headtohead"

    team1_id = team_dict[team1]["team_id"]
    team2_id = team_dict[team2]["team_id"]

    h2h = "{id1}-{id2}".format(id1=team1_id, id2=team2_id)
    date = f'{year:02}-{month:02}-{day:02}'
    # print(date)

    querystring = {"h2h": h2h, "date": date}

    response = requests.request("GET", url, headers=headers, params=querystring)
    loaded_r = json.loads(response.text)

    for fixture in loaded_r["response"]:
        fixture_id = fixture["fixture"]["id"]
        score_dict = fixture["score"]
        home_away = {"home": fixture["teams"]["home"]["name"], "away": fixture["teams"]["away"]["name"]}
        # print(home_away)

    # get fixture statistics
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/statistics"

    querystring = {"fixture": fixture_id}

    response = requests.request("GET", url, headers=headers, params=querystring)
    loaded_r = json.loads(response.text)

    curr_dict = {}

    for team in loaded_r["response"]:
        name = team["team"]["name"]

        stat = team["statistics"]
        temp = {}

        # add statistics to dict
        for curr in stat:
            curr_type, val = curr["type"], curr["value"]
            temp[curr_type] = val

        curr_dict[name] = temp

    # add halftime and fulltime score to statistics
    for ele in score_dict:
        home_score = score_dict[ele]["home"]
        away_score = score_dict[ele]["away"]

        home_team = home_away["home"]
        away_team = home_away["away"]

        curr_dict[home_team][ele] = home_score
        curr_dict[away_team][ele] = away_score

    return curr_dict

def get_key_stats(team1, team2, date):
    # get fixture id of mentioned match
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/headtohead"

    team1_id = team_dict[team1]["team_id"]
    team2_id = team_dict[team2]["team_id"]

    h2h = "{id1}-{id2}".format(id1=team1_id, id2=team2_id)
        # print(date)

    querystring = {"h2h": h2h, "date": date}

    response = requests.request("GET", url, headers=headers, params=querystring)
    loaded_r = json.loads(response.text)

    for fixture in loaded_r["response"]:
        fixture_id = fixture["fixture"]["id"]
        score_dict = fixture["score"]
        home_away = {"home": fixture["teams"]["home"]["name"], "away": fixture["teams"]["away"]["name"]}
        # print(home_away)

    # get fixture statistics
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/statistics"

    # return null if no games are found
    if not fixture_id:
        return None

    querystring = {"fixture": fixture_id}

    response = requests.request("GET", url, headers=headers, params=querystring)
    loaded_r = json.loads(response.text)

    curr_dict = {}

    for team in loaded_r["response"]:
        name = team["team"]["name"]

        stat = team["statistics"]
        temp = {}

        # add statistics to dict
        for curr in stat:
            curr_type, val = curr["type"], curr["value"]
            temp[curr_type] = val

        curr_dict[name] = temp

    # add halftime and fulltime score to statistics
    for ele in score_dict:
        home_score = score_dict[ele]["home"]
        away_score = score_dict[ele]["away"]

        home_team = home_away["home"]
        away_team = home_away["away"]

        curr_dict[home_team][ele] = home_score
        curr_dict[away_team][ele] = away_score

    return curr_dict

