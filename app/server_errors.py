class WsServerError(Exception):
    def __init__(self):
        self.message = super().__str__()


class GameNotStarted(WsServerError):
    def __init__(self):
        self.message = 'The game in this room is not started'


class IdAlreadyInUse(WsServerError):
    def __init__(self):
        self.message = 'Theres already connection with this id'
