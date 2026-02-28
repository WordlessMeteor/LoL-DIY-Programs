BOT_UUID: str = "00000000-0000-0000-0000-000000000000"
ALL_GAMEFLOW_PHASES: list[str] = [
    "None",
    "Lobby",
    "Matchmaking",
    "ReadyCheck",
    "CheckedIntoTournament",
    "ChampSelect",
    "GameStart",
    "InProgress",
    "Reconnect",
    "WaitingForStats",
    "PreEndOfGame",
    "EndOfGame",
    "FailedToLaunch",
    "TerminatedInError"
]
BOT_DIFFICULTY_LIST: list[str] = [
    "NONE",
    "TUTORIAL",
    "INTRO",
    "EASY",
    "MEDIUM",
    "HARD",
    "UBER",
    "RSWARMINTRO",
    "RSINTRO",
    "RSBEGINNER",
    "RSINTERMEDIATE"
]
SPECTATOR_POLICY_LIST: list[str] = [
    "LobbyAllowed",
    "FriendsAllowed",
    "AllAllowed",
    "NotAllowed"
]
GLOBAL_RESPONSE_LAG: float = 0.2
REPORT_CATEGORY_LIST_POSTGAME: list[str] = [
    "LEAVING_AFK",
    "ASSISTING_ENEMY_TEAM",
    "THIRD_PARTY_TOOLS",
    "RANK_MANIPULATION",
    "BOTTING",
    "VERBAL_ABUSE",
    "INAPPROPRIATE_NAME"
]
REPORT_CATEGORY_LIST_CHAMPSELECT: list[str] = [
    "UNSKILLED",
    "COMMS_ABUSE_TEXT",
    "SABOTAGING_TEAM",
    "DISRESPECTFUL_BEHAVIOR",
    "COMMS_ABUSE_VOICE",
    "INAPPROPRIATE_NAME",
    "OTHER"
]