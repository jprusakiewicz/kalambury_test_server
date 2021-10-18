import json
import random

from app.server_errors import LocaleNotSupported


class ClueManager:
    def __init__(self, locale):
        self.clue_dict = self.read_clue(locale)

    def read_clue(self, locale):
        path = ''
        if locale == 'pl':
            path = './clues/kalambury_dict_pl.txt'
        elif locale == 'en':
            path = './clues/kalambury_dict_en.txt'
        else:
            raise LocaleNotSupported
        with open(path, 'rt') as f:
            return json.loads(f.read())

    def get_new_clue(self) -> (str, str):
        category = random.choice(list(self.clue_dict.keys()))
        clue = random.choice(self.clue_dict[category])
        return category, clue
