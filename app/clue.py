import json
import random
import os
from app.server_errors import LocaleNotSupported


class ClueManager:
    def __init__(self, locale):
        self.clue_dict = self.read_clue(locale)
        self.used_clues = []

    def read_clue(self, locale):
        if locale in ['pl', 'en', 'es', 'de', 'fr', 'it']:
            path = './clues/kalambury_dict_' + locale + '.txt'
        else:
            raise LocaleNotSupported
        with open(path, 'rt') as f:
            return json.loads(f.read())

    def get_new_clue(self) -> (str, str):
        category = random.choice(list(self.clue_dict.keys()))
        clue = random.choice(self.clue_dict[category])
        if clue in self.used_clues:
            category, clue = self.get_new_clue()
            if len(self.used_clues) > 99:
                self.used_clues = self.used_clues[:-5]
        self.used_clues.append(clue)
        return category, clue
