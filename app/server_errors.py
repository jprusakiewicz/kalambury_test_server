class WsServerError(Exception):
    def __init__(self):
        self.message = super().__str__()


class GameNotStarted(WsServerError):
    def __init__(self):
        self.message = 'The game in this room is not started'


class PlayerIdAlreadyInUse(WsServerError):
    def __init__(self):
        self.message = 'Theres already connection with this id'


class NoRoomWithThisId(WsServerError):
    def __init__(self):
        self.message = 'Theres no room with this id'


class RoomIdAlreadyInUse(WsServerError):
    def __init__(self):
        self.message = 'Theres already room with this id'


class LocaleNotSupported(WsServerError):
    def __init__(self):
        self.message = 'Locale not supported'
