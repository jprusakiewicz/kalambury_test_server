import unittest

from app import ClueManager
from app.room import Room


class MyTestCase(unittest.TestCase):
    def test_getting_new_clue(self):
        c = ClueManager('pl')
        all_clues = []
        for idx in range(100):
            all_clues.append(c.get_new_clue())
        self.assertEqual(len(all_clues), len(set(all_clues)))  # add assertion here

    def test_guessing_word(self):
        # given
        room = Room(2, "en")
        room.clue = room.clue_manager.clue_dict["proverb"][0]

        self.assertTrue(room.check_players_clue("Don't count your chickens before they hatch"))
        self.assertTrue(room.check_players_clue("don't count your Chickens before they Hatch"))
        self.assertTrue(room.check_players_clue("don't count your Chickens ,before they hatch"))
        self.assertTrue(room.check_players_clue("don't count your Chickens ,before they hatch "))
        self.assertTrue(room.check_players_clue("don't count your Chickens ,before they hatch  "))
        self.assertTrue(room.check_players_clue("  don't count your Chickens ,before they hatch   "))


if __name__ == '__main__':
    unittest.main()
