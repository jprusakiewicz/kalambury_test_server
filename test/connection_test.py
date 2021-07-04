import unittest

from fastapi.testclient import TestClient

from main import app


class ConnectionManagerTest(unittest.TestCase):
    def test_single_connection(self):
        # given
        client = TestClient(app)
        test_client_id = 1
        expected_game_state = False
        expected_game_data = []
        expected_whos_turn = 0
        # when
        with client.websocket_connect(f"/ws/{test_client_id}") as websocket:
            data = websocket.receive_json()
        # then
        self.assertEqual(data['is_game_on'], expected_game_state)
        self.assertEqual(data['whos_turn'], expected_whos_turn)
        self.assertEqual(data['game_data'], expected_game_data)

    def test_double_connection(self):
        # given
        client = TestClient(app)
        test_client_one_id = 1
        test_client_two_id = 2
        expected_game_state = True
        expected_game_data = []
        expected_whos_turn = [1, 2]
        # when
        with client.websocket_connect(f"/ws/{test_client_one_id}") as websocket:
            _ = websocket.receive_json()

        with client.websocket_connect(f"/ws/{test_client_two_id}") as websocket:
            data = websocket.receive_json()
        # then
        self.assertEqual(data['is_game_on'], expected_game_state)
        self.assertIn(data['whos_turn'], expected_whos_turn)
        self.assertEqual(data['game_data'], expected_game_data)

    def test_broadcasting_on_draw(self):
        # given
        client = TestClient(app)
        test_client_one_id = 1
        test_client_two_id = 2
        expected_game_state = True
        expected_game_data = ["dupa"]
        expected_whos_turn = [1, 2]
        # when
        with client.websocket_connect(f"/ws/{test_client_one_id}") as websocket:
            _ = websocket.receive_json()

        with client.websocket_connect(f"/ws/{test_client_two_id}") as websocket:
            data = websocket.receive_json()
            kupadupa = websocket.send_json({"bytes": ["dupa"]})
            print(kupadupa)
        # then
        self.assertEqual(data['is_game_on'], expected_game_state)
        self.assertIn(data['whos_turn'], expected_whos_turn)
        self.assertEqual(data['game_data'], expected_game_data)

    def test_drawing_by_wrong_player(self):
        ...

    def test_changing_drawer_on_win(self):
        ...

    if __name__ == '__main__':
        unittest.main()
