#生涯（Profile）
challengeCrystalLevels: dict[str, str] = {
    "": "",
    "NONE": "",
    "IRON": "IRON",
    "BRONZE": "BRONZE",
    "SILVER": "SILVER",
    "GOLD": "GOLD",
    "PLATINUM": "PLATINUM",
    "EMERALD": "EMERALD",
    "DIAMOND": "DIAMOND",
    "MASTER": "MASTER",
    "GRANDMASTER": "GRANDMASTER",
    "CHALLENGER": "CHALLENGER"
}
titleAcquisitionTypes: dict[str, str] = {
    "": "",
    "DEFAULT": "DEFAULT",
    "CHALLENGE": "CHALLENGE",
    "CHAMPION_MASTERY": "CHAMPION_MASTERY",
    "EVENT": "EVENT"
}
challengeCategories: dict[str, str] = {
    "ALL": "All",
    "EXPERTISE": "Expertise",
    "TEAMWORK": "Teamwork & Strategy",
    "IMAGINATION": "Imagination",
    "VETERANCY": "Veterancy",
    "COLLECTION": "Collection",
    "LEGACY": "Legacy"
} #rcp-fe-lol-shared-components/global/default/trans-challenges.json
#英雄（Champion）
damageTypes: dict[str, str] = {
    "kPhysical": "Physical",
    "kMagic": "Magic",
    "kMixed": "Mixed"
}
attackTypes: dict[str, str] = {
    "melee": "melee",
    "ranged": "ranged"
}
#游戏模式（Game mode）
queueTypes_ranked: dict[str, str] = {
    "JADE_RANKED_SOLO_5x5": "League Classic 5x5",
    "RANKED_PREMADE_5x5": "5V5",
    "RANKED_TFT_DOUBLE_UP": "Double Up",
    "RANKED_TFT_PAIRS": "2V0",
    "RANKED_TFT_TURBO": "Hyper Roll",
    "RANKED_TFT": "Ranked TFT",
    "RANKED_FLEX_TT": "Twisted Treeline Flex 5V5",
    "CHERRY": "Arena",
    "RANKED_FLEX_SR": "Ranked Flex",
    "RANKED_SOLO_5x5": "Ranked Solo/Duo",
    "NONE": "None"
}
categories: dict[str, str] = {
    "Custom": "Custom",
    "PvP": "PvP",
    "VersusAi": "VersusAi"
}
gameSelectCategories: dict[str, str] = {
    "": "",
    "CreateCustom": "Create Custom",
    "JoinCustom": "Join Custom",
    "kPvP": "PvP",
    "kTraining": "Training",
    "kVersusAI": "Co-op vs. AI"
}
gameSelectModeGroups: dict[str, str] = {
    "": "",
    "kARAM": "ARAM",
    "kAlternativeLeagueGameModes": "Alternate League Modes",
    "kSummonersRift": "Summoner's Rift",
    "kTeamfightTactics": "Teamfight Tactics",
    "kJade": "Jade"
}
banModes: dict[str, str] = {
    "": "",
    "SkipBanStrategy": "SkipBanStrategy",
    "StandardBanStrategy": "StandardBanStrategy",
    "TournamentBanStrategy": "TournamentBanStrategy"
}
pickModes: dict[str, str] = {
    "": "",
    "AllRandomPickStrategy": "AllRandomPickStrategy",
    "AllTeamVotePickStrategy": "AllTeamVotePickStrategy",
    "CounterDraftPickStrategy": "CounterDraftPickStrategy",
    "DraftModeSinglePickStrategy": "DraftModeSinglePickStrategy",
    "OneTeamVotePickStrategy": "OneTeamVotePickStrategy",
    "QuickplayPickStrategy": "QuickplayPickStrategy",
    "SimulPickStrategy": "SimulPickStrategy",
    "SkipPickStrategy": "SkipPickStrategy",
    "TeamBuilderDraftPickStrategy": "TeamBuilderDraftPickStrategy",
    "TournamentPickStrategy": "TournamentPickStrategy"
}
#排位信息（Ranked）
tiers: dict[str, str] = {
    "": "",
    "NONE": "NONE",
    "IRON": "Iron",
    "BRONZE": "Bronze",
    "SILVER": "Silver",
    "GOLD": "Gold",
    "PLATINUM": "Platinum",
    "EMERALD": "Emerald",
    "DIAMOND": "Diamond",
    "MASTER": "Master",
    "GRANDMASTER": "Grandmaster",
    "CHALLENGER": "Challenger",
    "SALT": "Salt",
    "WOOD": "Wood",
    "LEGEND": "Legend",
}
ratedTiers_turbo: dict[str, str] = {
    "": "",
    "NONE": "NONE",
    "GRAY": "GRAY TIER",
    "GREEN": "GREEN TIER",
    "BLUE": "BLUE TIER",
    "PURPLE": "PURPLE TIER",
    "ORANGE": "HYPER TIER"
}
ratedTiers_cherry: dict[str, str] = {
    "": "",
    "NONE": "NONE",
    "GRAY": "WOOD TIER",
    "GREEN": "BRONZE TIER",
    "BLUE": "SILVER TIER",
    "PURPLE": "GOLD TIER",
    "ORANGE": "GLADIATOR TIER"
}
#英雄联盟对局记录（LoL match history）
gameTypes_history: dict[str, str] = {
    "MATCHED_GAME": "MATCHED_GAME",
    "CUSTOM_GAME": "CUSTOM_GAME",
    "TUTORIAL_GAME": "TUTORIAL_GAME"
}
team_colors_int: dict[int, str] = {
    0: "",
    1: "Blue",
    2: "Red",
    3: "Neutral",
    100: "Blue",
    200: "Red",
    300: "Neutral"
}
team_colors_str: dict[str, str] = {
    "0": "",
    "1": "Blue",
    "2": "Red",
    "3": "Neutral",
    "100": "Blue",
    "200": "Red",
    "300": "Neutral",
    "ORDER": "Order",
    "CHAOS": "Chaos"
}
endOfGameResults: dict[str, str] = {
    "": "",
    "GameComplete": "GameComplete",
    "Abort_Unexpected": "Abort_Unexpected",
    "Abort_TooFewPlayers": "Abort_TooFewPlayers",
    "Abort_AntiCheatExit": "Abort_AntiCheatExit"
}
lanes: dict[str, str] = {
    "TOP": "TOP",
    "JUNGLE": "JUNGLE",
    "MIDDLE": "MIDDLE",
    "BOTTOM": "BOTTOM",
    "NONE": ""
}
roles: dict[str, str] = {
    "CARRY": "CARRY",
    "DUO": "DUO",
    "SOLO": "SOLO",
    "SUPPORT": "SUPPORT",
    "NONE": ""
}
#英雄联盟对局概要（LoL match summary）
subteam_colors: dict[int, str] = {
    0: "",
    1: "Poro",
    2: "Minion",
    3: "Scuttle",
    4: "Krug",
    5: "Raptor",
    6: "Sentinel",
    7: "Wolf",
    8: "Gromp"
}
augment_rarity: dict[int | str, str] = {
    0: "Silver",
    1: "Gold",
    2: "Prismatic",
    4: "Gold",
    8: "Prismatic",
    "KBronze": "Bronze",
    "KSilver": "Silver",
    "kGold": "Gold",
    "kPrismatic": "Prismatic",
    "kEventChoice": "Event"
}
#英雄联盟事件（LoL events）
eventTypes: dict[str, str] = {
    "BUILDING_KILL": "Building Kills",
    "CHAMPION_KILL": "Champion Kills",
    "CHAMPION_SPECIAL_KILL": "Special Kills",
    "CHAMPION_TRANSFORM": "Champion Transform",
    "DRAGON_SOUL_GIVEN": "Dragon Soul Assigned",
    "ELITE_MONSTER_KILL": "Elite Monster Kills",
    "FEAT_UPDATE": "Update Feats of Strength",
    "GAME_END": "Game End",
    "ITEM_DESTROYED": "Remove Items",
    "ITEM_PURCHASED": "Purchase Items",
    "ITEM_SOLD": "Sell Items",
    "ITEM_UNDO": "Redo Items",
    "LEVEL_UP": "Level Up",
    "OBJECTIVE_BOUNTY_FINISH": "Finish Objective Bounty",
    "OBJECTIVE_BOUNTY_PRESTART": "Wait for Objective Bounty",
    "PAUSE_END": "Loading Completes",
    "SKILL_LEVEL_UP": "Level Up Skill",
    "TURRET_PLATE_DESTROYED": "Destroy Turret Plates",
    "WARD_KILL": "Wards Kills",
    "WARD_PLACED": "Wards Placed"
}
buildingTypes: dict[str, str] = {
    "": "",
    "INHIBITOR_BUILDING": "Inhibitor",
    "TOWER_BUILDING": "Turret"
}
featTypes: dict[int, str] = {
    0: "Feat of Warfare",
    1: "Feat of First Turret",
    2: "Feat of Monster Kill"
}
laneTypes: dict[str, str] = {
    "": "",
    "TOP_LANE": "Top",
    "MID_LANE": "Middle",
    "BOT_LANE": "Bottom"
}
levelUpTypes: dict[str, str] = {
    "NORMAL": "NORMAL",
    "EVOLVE": "EVOLVE"
}
killTypes: dict[str, str] = {
    "KILL_ACE": "Ace",
    "KILL_FIRST_BLOOD": "First Blood",
    "KILL_MULTI": "Multikill",
}
monsterSubTypes: dict[str, str] = {
    "": "",
    "EARTH_DRAGON": "Mountain Drake",
    "CHEMTECH_DRAGON": "Chemtech Drake",
    "WATER_DRAGON": "Ocean Drake",
    "HEXTECH_DRAGON": "Hextech Drake",
    "AIR_DRAGON": "Cloud Drake",
    "FIRE_DRAGON": "Infernal Drake",
    "ELDER_DRAGON": "Elder Dragon",
    "RUINED_DRAGON": "Ruined Dragon",
    "UNKNOWN": "Unknown"
}
monsterTypes: dict[str, str] = {
    "": "",
    "RIFTHERALD": "Rift Herald",
    "HORDE": "Voidgrub",
    "BARON_NASHOR": "Baron Nashor",
    "DRAGON": "Drake",
    "ATAKHAN": "Atakhan"
}
dragonSoul_names: dict[str, str] = {
    "Infernal": "Infernal",
    "Mountain": "Mountain",
    "Ocean": "Ocean",
    "Cloud": "Cloud",
    "Chemtech": "Chemtech",
    "Hextech": "Hextech",
    "Ruined": "Ruined",
    "Party": "Party"
}
towerTypes: dict[str, str] = {
    "": "",
    "OUTER_TURRET": "Outer Turret",
    "INNER_TURRET": "Inner Turret",
    "BASE_TURRET": "Inhibitor Turret",
    "NEXUS_TURRET": "Nexus Turret"
}
transformTypes: dict[str, str] = {
    "ASSASSIN": "ASSASSIN",
    "SLAYER": "RHAAST"
}
wardTypes: dict[str, str] = {
    "BLUE_TRINKET": "Farsight Alteration",
    "CONTROL_WARD": "Control Ward",
    "SIGHT_WARD": "Sightstone",
    "TEEMO_MUSHROOM": "Mushroom",
    "UNDEFINED": "Unknown",
    "VISION_WARD": "Vision Ward",
    "YELLOW_TRINKET": "Stealth Ward",
}
eventTypes_liveclient: dict[str, str] = {
    "Ace": "Ace",
    "AtakhanKill": "AtakhanKill",
    "BaronKill": "BaronKill",
    "ChampionKill": "ChampionKill",
    "DragonKill": "DragonKill",
    "FirstBlood": "FirstBlood",
    "FirstBrick": "FirstTurret",
    "GameEnd": "GameEnd",
    "GameStart": "GameStart",
    "HeraldKill": "HeraldKill",
    "HordeKill": "VoidgrubKill",
    "InhibKilled": "InhibitorKilled",
    "MinionsSpawning": "MinionsSpawning",
    "Multikill": "Multikill",
    "TurretKilled": "TurretKilled"
}
DragonTypes: dict[str, str] = {
    "Air": "Cloud Drake",
    "Earth": "Mountain Drake",
    "Fire": "Infernal Drake",
    "Water": "Ocean Drake",
    "Chemtech": "Chemtech Drake",
    "Hextech": "Hextech Drake",
    "Elder": "Elder Drake",
    "Ruined": "Ruined Dragon",
    "Party": "Party Drake"
}
#云顶之弈对局记录（TFT match history）
traitStyles: dict[int, str] = {
    0: "",
    1: "Bronze",
    2: "Silver",
    3: "Gold",
    4: "Prismatic",
    5: "Unique"
}
rarities: dict[str, str] = {
    "Default": "Default",
    "NoRarity": "Others",
    "Common": "Common",
    "Epic": "Epic",
    "Legacy": "Legacy",
    "Legendary": "Legendary",
    "Mythic": "Mythic",
    "Rare": "Rare",
    "Ultimate": "Ultimate",
    "Exalted": "Exalted",
    "Transcendant": "Transcendant"
}
#自定义房间（Custom lobby）
spectatorPolicies: dict[str, str] = {
    "LOBBYONLY": "Lobby Only",
    "LOBBY": "Lobby Only",
    "DROPINONLY": "Friends List Only",
    "DROPIN": "Friends List Only",
    "ALL": "All",
    "NONE": "None"
}
botDifficulty_dict: dict[str, str] = {
    "NONE": "NONE",
    "TUTORIAL": "TUTORIAL",
    "INTRO": "INTRO",
    "EASY": "EASY",
    "MEDIUM": "MEDIUM",
    "HARD": "HARD",
    "UBER": "UBER",
    "RSWARMINTRO": "RSWARMINTRO",
    "RSINTRO": "RSINTRO",
    "RSBEGINNER": "RSBEGINNER",
    "RSINTERMEDIATE": "RSINTERMEDIATE",
    "MLINTRO": "MLINTRO"
}
positions: dict[str, str] = {
    "": "",
    "NONE": "NONE",
    "Invalid": "", #Unavailable
    "AFK": "AFK",
    "UNSELECTED": "UNSELECTED",
    "TOP": "TOP",
    "JUNGLE": "JUNGLE",
    "MIDDLE": "MIDDLE",
    "BOTTOM": "BOTTOM",
    "UTILITY": "UTILITY",
    "FILL": "FILL"
}
#商品藏品（Store and collection）
krarities: dict[str, str] = {
    "kNoRarity": "Other",
    "kExalted": "Exalted",
    "kEpic": "Epic",
    "kLegendary": "Legendary",
    "kMythic": "Mythic",
    "kRare": "Rare",
    "kUltimate": "Ultimate",
    "kTranscendent": "Transcendant"
}
skinClassifications: dict[str, str] = {
    "": "",
    "kChampion": "Skin",
    "kGeneric": "Generic",
    "kRecolor": "Recolor"
}
inventoryType_dict: dict[str, str] = {
    "ACHIEVEMENT_BANNER_ACCENT": "Banner Skin",
    "ACHIEVEMENT_TITLE": "Title",
    "ANNOUNCER_PACK": "ANNOUNCER_PACK",
    "ARAM_BOON": "ARAM_BOON",
    "AUGMENT": "AUGMENT",
    "AUGMENT_SLOT": "AUGMENT_SLOT",
    "BOOST": "Boost",
    "BUNDLES": "Bundle",
    "CHAMPION": "Champion",
    "CHAMPION_PERMANENT": "Champion Permanent",
    "CHAMPION_SKIN": "Champion Skin",
    "CHERRY_BOON": "Arena season journey",
    "COMPANION": "Companion",
    "CURRENCY": "Currency",
    "EMOTE": "Emote",
    "EVENT_PASS": "Event Pass",
    "FANPASS": "Fan Pass",
    "GIFT": "Gift",
    "HEXTECH_CRAFTING": "Loot",
    "JADE_RUNE": "Rune",
    "JADE_RUNE_GLYPH": "Glyph",
    "JADE_RUNE_MARK": "Mark",
    "JADE_RUNE_PAGE": "Rune page (Jade)",
    "JADE_RUNE_QUINTESSENCE": "Quintessence",
    "JADE_RUNE_SEAL": "Seal",
    "JADE_RUNE_SLOT": "Rune Slot",
    "MEGA_BUNDLE": "Mega Bundle",
    "MODE_PROGRESSION_REWARD": "MODE_PROGRESSION_REWARD",
    "MYSTERY": "Mystery Item",
    "NEXUS_FINISHER": "Nexus Finisher",
    "OPAL_ACHIEVEMENT": "Demacia Rising Achievement",
    "PORTRAIT": "Portrait",
    "PREMIUM_CLUB_MEMBERSHIP": "PREMIUM_CLUB_MEMBERSHIP",
    "PROGRESSION": "Progression",
    "PROVIEW_PASS": "PROVIEW_PASS",
    "PVE_RELIC": "PVE_RELIC",
    "PVE_SUMMONER_PACKAGE": "PVE_SUMMONER_PACKAGE",
    "PVE_UPGRADE": "PVE_UPGRADE",
    "QUEUE_ENTRY": "QUEUE_ENTRY",
    "REGALIA_BANNER": "Banner",
    "REGALIA_BORDER": "Ranked Border",
    "REGALIA_CREST": "Ranked Crest",
    "RP": "RP",
    "RUNE": "Rune Page",
    "SKIN_AUGMENT": "Skin Augment",
    "SKIN_BORDER": "Border",
    "SKIN_UPGRADE_GEAR": "SKIN_UPGRADE_GEAR",
    "SKIN_UPGRADE_HOME_GUARD": "SKIN_UPGRADE_HOME_GUARD",
    "SKIN_UPGRADE_RECALL": "SKIN_UPGRADE_RECALL",
    "SKIN_UPGRADE_SPAWN": "SKIN_UPGRADE_SPAWN",
    "SPELL_BOOK_PAGE": "Rune Page",
    "STATSTONE": "Eternal",
    "STRAWBERRY_BOON": "STRAWBERRY_BOON",
    "STRAWBERRY_LOADOUT_ITEM": "STRAWBERRY_LOADOUT_ITEM",
    "STRAWBERRY_MAP": "STRAWBERRY_MAP",
    "SUMMONER_CUSTOMIZATION": "SUMMONER_CUSTOMIZATION",
    "SUMMONER_ICON": "Summoner Icon",
    "TEAMPASS": "Team Pass",
    "TEAM_SKIN_PURCHASE": "TEAM_SKIN_PURCHASE",
    "TFT_DAMAGE_SKIN": "Boom",
    "TFT_EVENT_HEALTH_BADGE": "TFT_EVENT_HEALTH_BADGE",
    "TFT_EVENT_PLAYER_TAG": "TFT_EVENT_PLAYER_TAG",
    "TFT_EVENT_PVE_BUDDY": "Guides",
    "TFT_EVENT_PVE_DIFFICULTY": "TFT_EVENT_PVE_DIFFICULTY",
    "TFT_EVENT_RIBBON": "TFT_EVENT_RIBBON",
    "TFT_EVENT_SKILLS": "Skin Bonuses",
    "TFT_MAP_SKIN": "Arena Skin",
    "TFT_PLAYBOOK": "Legend",
    "TFT_ZOOM_SKIN": "Portals",
    "TOURNAMENT_FLAG": "Clash Banners",
    "TOURNAMENT_FRAME": "TOURNAMENT_FRAME",
    "TOURNAMENT_LOGO": "Clash Logos",
    "TOURNAMENT_TROPHY": "Clash Trophies",
    "TRANSFER": "Account Transfer",
    "WARD_SKIN": "Ward Skin"
}
ownershipTypes: dict[None | str, str] = {
    None: "Unowned",
    "F2P": "Free to play",
    "LOYALTY": "Rewards Programs",
    "RENTED": "Rented",
    "OWNED": "Owned"
}
subInventoryTypes: dict[None | str, str] = {
    None: "",
    "": "",
    "BORDER_SET_BUNDLE": "Border Set Bundle",
    "CHEST": "Hextech Chest",
    "CHAMPION_BUNDLE": "CHAMPION_BUNDLE",
    "CHROMA_BUNDLE": "Chroma Bundle",
    "CURRENCY": "Currency",
    "EMOTE_BUNDLE": "EMOTE_BUNDLE",
    "HEXTECH_BUNDLE": "HEXTECH_BUNDLE",
    "LOL_EVENT_PASS": "LOL_EVENT_PASS",
    "MATERIAL": "Material",
    "RECOLOR": "Recolor",
    "RUNE_PAGE_BUNDLE": "RUNE_PAGE_BUNDLE",
    "SKIN_BUNDLE": "Skin Bundle",
    "SKIN_VARIANT_BUNDLE": "Variant Skin Bundle",
    "TFT_PASS": "TFT_PASS",
    "TFT_TREASURE_TROVE_TOKEN": "Treasure Token",
    "mgs_opal_shield": "OpalSilverShield",
    "lol_clash_premium_tickets": "Premium Clash Tickets",
    "lol_clash_tickets": "Basic Clash Tickets",
    "lol_blessing_token": "Ancient Spark",
    "lol_blue_essence": "Blue Essence",
    "lol_mythic_essence": "Mythic Essence",
    "lol_orange_essence": "Orange Essence",
    "lol_rare_gem": "Rare Gemstone",
    "tft_star_fragments": "Star Shards"
} #非全大写的值表示在游戏数据中找到了对应的描述（Not all letters being in capital means relevant descriptions are found from the game data）
#战利品（Loot）
essenceTypes: dict[str, str] = {
    "CURRENCY_champion": "Blue Essence",
    "CURRENCY_cosmetic": "Orange Essence",
    "": ""
}
lootCategories: dict[str, str] = {
    "": "Others",
    "CHAMPION": "CHAMPION",
    "CHEST": "CHEST",
    "COMPANION": "COMPANION",
    "EMOTE": "EMOTE",
    "ETERNALS": "ETERNALS",
    "SKIN": "SKIN",
    "SUMMONERICON": "SUMMONERICON",
    "WARDSKIN": "WARDSKIN"
}
itemStatus_dict: dict[str, str] = {
    "NONE": "NONE",
    "FREE": "FREE",
    "RENTAL": "RENTAL",
    "OWNED": "OWNED"
}
lootRarities: dict[str, str] = {
    "": "NONE",
    "DEFAULT": "DEFAULT",
    "EPIC": "Epic",
    "LEGENDARY": "Legendary",
    "MYTHIC": "Mythic",
    "ULTIMATE": "Ultimate"
}
redeemableStatus_dict: dict[str, str] = {
    "ALREADY_OWNED": "Owned",
    "ALREADY_RENTED": "Rented",
    "CHAMPION_NOT_OWNED": "Champion Not Owned",
    "NOT_REDEEMABLE": "Cannot be Unlocked",
    "NOT_REDEEMABLE_RENTAL": "Cannot be Activated",
    "REDEEMABLE": "Unlockable",
    "REDEEMABLE_RENTAL": "Activatable",
    "NOT_UPGRADE": "No Upgrade"
}
lootTypes: dict[str, str] = {
    "": "Others",
    "BOOST": "Boost",
    "BUNDLE": "Bundle",
    "CHAMPION": "Champion Permanent",
    "CHAMPION_RENTAL": "Champion Shard",
    "CHAMPION_TOKEN": "=Mastery Token",
    "CHROMA": "Chroma Permanent",
    "CHROMA_RENTAL": "Chroma Shard",
    "CHEST": "Chest",
    "COMPANION": "Tactician Permanent",
    "CURRENCY": "Currency",
    "EMOTE": "Emote Permanent",
    "EMOTE_RENTAL": "Emote Shard",
    "MATERIAL": "Material",
    "NEXUS_FINISHER": "Nexus Finisher",
    "SKIN": "Skin Permanent",
    "SKIN_RENTAL": "Skin Shard",
    "STATSTONE": "Eternals Set Permanent",
    "STATSTONE_SHARD": "Eternals Set Shard",
    "SUMMONERICON": "Summoner Icon",
    "TFT_DAMAGE_SKIN": "Boom",
    "TFT_MAP_SKIN": "Arena Skin",
    "TOURNAMENTLOGO": "Logo",
    "WARDSKIN": "Ward Skin Permanent",
    "WARDSKIN_RENTAL": "Ward Skin Shard"
}
#聊天服务（Chat service）
RiotRelationships: dict[str, str] = {
    "friend": "friend"
}
ptyTypes: dict[str, str] = {
    "open": "open",
    "closed": "closed"
}
conversationTypes: dict[str, str] = {
    "chat": "Friend chat",
    "customGame": "Custom Game",
    "championSelect": "Champion Select",
    "postGame": "End of Game"
}
messageTypes: dict[str, str] = {
    "chat": "Friend chat",
    "groupchat": "Party",
    "system": "System",
    "information": "Information",
    "celebration": "Celebration"
}
system_messages: dict[str, str] = {
    "starting_soon": "[System Notification] Your match will start soon. Please wait as we load up your game. This process should not take more than a few minutes.",
    "connecting": "Connecting...",
    "disconnected": "You've been disconnected from chat, attempting to reconnect…",
    "dropped_message": "The message is restricted and could not be sent.",
    "is_blocked": "{actor} is on your block list. You will not see their chat messages.",
    "joined_room": "{actor} joined the lobby",
    "left_room": "{actor} left the lobby",
    "no_friends": "Looks like you haven't added any friends yet.  Invite friends to chat and play together.",
    "no_online_friends": "Looks like no one is home. Did you know you can send messages to friends who are offline?~",
    "rich_content_replaced": "Please check the message in the League of Legends mobile app.",
    "TEXT_CHAT_MUTED": "You are chat restricted for creating a negative experience for other players.",
    "chat_restriction_muted": "You are chat restricted for creating a negative experience for other players.",
    "TEXT_CHAT_RESTRICTION": "You are chat restricted for creating a negative experience for other players.",
    "TEXT_CHAT_MUTED_LIFTED": "You are no longer chat restricted. Remember, clear and respectful communication is essential to be a team that wins together.",
    "TEXT_CHAT_RESTRICTION_LIFTED": "You are no longer chat restricted. Remember, clear and respectful communication is essential to be a team that wins together."
}
invidStates: dict[str, str] = {
    "Pending": "Pending",
    "OnHold": "OnHold"
}
invidTypes: dict[str, str] = {
    "party": "Party",
    "lobby": "Lobby"
}
availabilities: dict[str, str] = {
    "available": "Available",
    "away": "Away",
    "championSelect": "Champ Select",
    "chat": "Online",
    "dnd": "In Game",
    "hostingCoopVsAIGame": "Creating Co-op vs. AI Game",
    "hostingFeaturedGame": "Creating Featured Game",
    "hostingNormalGame": "Creating Normal Game",
    "hostingPracticeGame": "Creating Custom Game",
    "hostingRankedGame": "Creating Ranked Game",
    "hosting_ARAM_UNRANKED_5x5": "Creating Normal Game",
    "hosting_BOT": "Creating Co-op vs. AI Game",
    "hosting_BOT_3x3": "Creating Co-op vs. AI Game",
    "hosting_BRAWL": "Creating Brawl Game",
    "hosting_CHERRY": "Creating Arena Game",
    "hosting_KIWI": "Creating ARAM: Mayhem Game",
    "hosting_RIOTSCRIPT_BOT": "Creating Co-op vs. AI Game",
    "hosting_Custom": "Creating Custom Game",
    "hosting_NEXUSBLITZ": "Creating Nexus Blitz Game",
    "hosting_NORMAL": "Creating Normal Game",
    "hosting_NORMAL_3x3": "Creating Normal Game",
    "hosting_NORMAL_TFT": "Creating TFT Game",
    "hosting_PRACTICETOOL": "Creating Practice Game",
    "hosting_RANKED_FLEX_SR": "Creating Ranked Game",
    "hosting_RANKED_FLEX_TT": "Creating Ranked Game",
    "hosting_RANKED_SOLO_5x5": "Creating Ranked Game",
    "hosting_RANKED_TEAM_5x5": "Creating Ranked Game",
    "hosting_RANKED_TFT": "Creating TFT Game",
    "hosting_RANKED_TFT_TURBO": "Creating TFT Game",
    "hosting_RANKED_TFT_PAIRS": "Creating Double Up Game",
    "hosting_RANKED_TFT_DOUBLE_UP": "Creating Double Up Game",
    "hosting_RANKED_PREMADE_5x5": "Creating Ranked 5s Game",
    "hosting_STRAWBERRY": "Creating Swarm Game",
    "hosting_SWIFTPLAY": "Creating Swiftplay Game",
    "hosting_CHONCC_TREASURE_TFT": "Creating TFT Game",
    "hosting_LNY23_TFT": "Creating TFT Game",
    "hosting_LNY24_TFT": "Creating TFT Game",
    "hosting_LNY25_TFT": "Creating TFT Game",
    "hosting_SET_REVIVAL_5_5_TFT": "Creating TFT Game",
    "hosting_SET_REVIVAL_TFT": "Creating TFT Game",
    "hosting_FIVE_YEAR_ANNIVERSARY_TFT": "Creating TFT Game",
    "hosting_SF_TFT": "Creating TFT Game",
    "hosting_PVE_PUZZLE_TFT": "Creating TFT Game",
    "hosting_featured": "Creating Featured Game",
    "inGame": "In Game",
    "inQueue": "In Queue",
    "inTeamBuilder": "In Team Builder",
    "map_hosting_ARAM_UNRANKED_5x5": "Creating Normal Game (Howling Abyss)",
    "map_hosting_NORMAL": "Creating Normal Game (Summoner's Rift)",
    "map_hosting_NORMAL_3x3": "Creating Normal Game (Twisted Treeline)",
    "map_hosting_RANKED_FLEX_SR": "Creating Ranked Flex Game (Summoner's Rift)",
    "map_hosting_RANKED_PREMADE_5x5": "Creating Ranked 5s Game (Summoner's Rift)",
    "map_hosting_RANKED_FLEX_TT": "Creating Ranked Flex Game (Twisted Treeline)",
    "mobile": "Riot Mobile",
    "offline": "Offline",
    "online": "Online",
    "discord": "Discord",
    "spectating": "Spectating",
    "teamSelect": "In Team Select",
    "tutorial": "In Tutorial",
    "undefined": "Pending...",
    "watchingReplay": "Watching Replay",
    "outOfGame": "在线",
    "hosting_PROMETHIUM_TFT": "Creating Ao Shin's Ascent Game",
    "hosting_URF": "Creating URF Game"
} #来源（Source）：plugins/rcp-fe-lol-social/global/default/trans.json
#目标和任务（Objective and mission）
celebrationTypes: dict[str, str] = {
    "NONE": "NONE",
    "FULLSCREEN": "FULLSCREEN",
    "TOAST": "Toast",
    "VIGNETTE": "VIGNETTE",
    "VIGNETTE_LARGE_REWARDS_ONLY": "VIGNETTE_LARGE_REWARDS_ONLY",
    "VIGNETTE_REWARDS_ONLY": "VIGNETTE_REWARDS_ONLY"
}
clientNotifyLevels: dict[str, str] = {
    "ALWAYS": "ALWAYS",
    "NONE": "NONE"
}
displayTypes: dict[str, str] = {
    "AFTER_COMPLETION": "AFTER_COMPLETION",
    "ALWAYS": "ALWAYS",
    "CELEBRATION_ONLY": "CELEBRATION_ONLY",
    "NONE": "NONE",
    "TUTORIAL_ONLY": "TUTORIAL_ONLY"
}
missionTypes: dict[str, str] = {
    "ONETIME": "ONETIME",
    "REPEATING": "REPEATING"
}
metadataMissionTypes: dict[str, str] = {
    "": "",
    "always": "always"
}
objectiveStatus_dict: dict[str, str] = {
    "DUMMY": "DUMMY",
    "ELIGIBLE": "ELIGIBLE",
    "INELIGIBLE": "INELIGIBLE"
}
objectiveTypes: dict[str, str] = {
    "": "",
    "CHAMPION_MASTERY": "Champion Mastery",
    "EOGDATA": "EOGDATA",
    "INGEST": "INGEST",
    "LEGS": "LEGS",
    "SERIES_COMPLETION": "SERIES_COMPLETION",
    "TFT_ELIMINATION": "TFT_ELIMINATION"
}
rewardGroupStrategies: dict[str, str] = {
    "": "",
    "ALL_GROUPS": "ALL_GROUPS",
    "SELECT_GROUPS": "SELECT_GROUPS",
    "OBJECTIVE_GROUPS": "OBJECTIVE_GROUPS"
}
rewardTypes: dict[str, str] = {
    "BLUE_ESSENCE": "Blue Essence",
    "BOOST": "IP Boost",
    "BUNDLE": "Bundle",
    "CHAMPION": "Champion",
    "CHAMPION_CHROMA": "Champion Chroma",
    "CHAMPION_SHARD": "Champion Shard",
    "CHAMPION_SKIN": "Champion Skin",
    "CHAMPION_SKIN_SHARD": "Champion Skin Shard",
    "CHAMPION_TOKEN": "Champion Mastery Token",
    "CLASH_TICKET": "Clash Ticket",
    "CLIENT_FEATURE": "Client Feature",
    "EMOTE": "Emote",
    "EVENT_MATERIAL": "Event Material",
    "GAME_QUEUE": "GAME_QUEUE",
    "GEMSTONE": "Gemstone",
    "HEXTECH_CHEST": "Loot Chest",
    "HEXTECH_KEY": "Hextech Key",
    "HEXTECH_KEY_SHARD": "Hextech Key Fragment",
    "IP": "IP",
    "MISSION_PROGRESS": "MISSION_PROGRESS",
    "MYSTERY_SKIN": "Mystery Skin",
    "ORANGE_ESSENCE": "Orange Essence",
    "PROGRESSION": "PROGRESSION",
    "PORTAL": "Portal",
    "PORTAL_KEY": "Portal Key",
    "PORTAL_KEY_SHARD": "Portal Key Shard",
    "REWARD_GROUP": "REWARD_GROUP",
    "REWARDS_TITLE": "Mission Reward",
    "REWARDS_TITLE_MULTI": "Mission Rewards",
    "RIOT_POINTS": "RIOT_POINTS",
    "SPELL_BOOK_PAGE": "SPELL_BOOK_PAGE",
    "SUMMONER_ICON": "Summoner Icon",
    "SUMMONER_ICON_SHARD": "Summoner Icon Shard",
    "SUMMONER_SPELL": "SUMMONER_SPELL",
    "WARD_SKIN": "Ward Skin",
    "WARD_SKIN_SHARD": "Ward Skin Shard",
    "XP": "XP"
} #来源（Source）：rcp-fe-lol-navigation/global/default/trans.json
missionStatus_dict: dict[str, str] = {
    "COMPLETED": "COMPLETED",
    "DUMMY": "DUMMY",
    "PENDING": "PENDING",
    "SELECT_REWARDS": "SELECT_REWARDS",
    "UPCOMING": "UPCOMING"
}
gameTypes_mission: dict[str, str] = {
    "lol": "LoL",
    "tft": "TFT"
}
objectivesTypes: dict[str, str] = {
    "kNonPooledObjectives": "kNonPooledObjectives",
    "kPooledObjectives": "kPooledObjectives"
}
lolObjectiveCategoryTypes: dict[str, str] = {
    "kNonPass": "kNonPass",
    "kEventHubConfiguration": "kEventHubConfiguration",
    "kTFTPassData": "kTFTPassData"
}
lolEventHubTypes: dict[str, str] = {
    "NON_PASS": "NON_PASS",
    "SEASON_PASS": "SEASON_PASS"
}
objectiveCategoryFilter_dict: dict[str, str] = {
    "kNone": "kNone",
    "kNPE": "kNPE"
}
eventPassTypes: dict[str, str] = {
    "kUnknown": "kUnknown",
    "kActivityCenterMilestones": "kActivityCenterMilestones",
    "kBattlePass": "kBattlePass",
    "kDemaciaPass": "kDemaciaPass",
    "kEventPass": "kEventPass",
    "kSeasonPass": "kSeasonPass"
}
#符文（Perk）
slotTypes: dict[str, str] = {
    "": "",
    "kKeyStone": "KeyStone",
    "kMixedRegularSplashable": "Perk",
    "kStatMod": "StatMod"
}
recommendedAttributes: dict[str, str] = {
    "kBurstDamage": "Burst Damage",
    "kCooldown": "Cooldown",
    "kDamagePerSecond": "DPS",
    "kDurability": "Durability",
    "kGold": "Gold",
    "kHealing": "Healing",
    "kMana": "Mana",
    "kMoveSpeed": "Movespeed",
    "kUtility": "Utility"
} #来源（Source）：rcp-fe-lol-collections/global/default/trans-perks.json
#对局结算（End of game）
honorType_tooltip_headers: dict[str, str] = {
    "COOL": "Stayed cool",
    "SHOTCALLER": "Great shotcalling",
    "HEART": "GG <3"
}
honorType_tooltip_bodies: dict[str, str] = {
    "COOL": "Tilt-proof, chill",
    "SHOTCALLER": "Leadership, strategy",
    "HEART": "Team player, friendly"
}
#装备（Item）
itemCategories: dict[str, str] = {
    "AbilityHaste": "Ability Haste",
    "Active": "Active",
    "Armor": "Armor",
    "ArmorPenetration": "Armor Penetration",
    "AttackSpeed": "Attack Speed",
    "Aura": "Aura",
    "Bilgewater": "Bilgewater",
    "Boots": "Boots",
    "Consumable": "Consumable",
    "CooldownReduction": "Cooldown Reduction",
    "CriticalStrike": "Critical Strike",
    "Damage": "Attack Damage",
    "GoldPer": "Gold",
    "Health": "Health",
    "HealthRegen": "Health Regen",
    "Jungle": "Jungle",
    "Lane": "Lane",
    "LifeSteal": "Life Steal",
    "MagicPenetration": "Magic Penetration",
    "MagicResist": "Magic Resistance",
    "Mana": "Mana",
    "ManaRegen": "Mana Regen",
    "Movement": "Movement Speed",
    "NonbootsMovement": "Non-boots Movement",
    "OnHit": "On-Hit",
    "Slow": "Slow",
    "SpellBlock": "Spell Block",
    "SpellDamage": "Ability Power",
    "SpellVamp": "Spell Vamp",
    "Stealth": "Stealth",
    "Tenacity": "Tenacity",
    "Trinket": "Trinket",
    "Vision": "Vision"
}
#事件通行证（Event pass）
rewardTag_dict: dict[str, str] = {
    "Multiple": "Multiple",
    "Choice": "Choice",
    "Instant": "Instant",
    "Free": "Free",
    "Rare": "Rare"
}
lolEventHubRewardTrackItemStates: dict[str, str] = {
    "Selected": "Selected",
    "Unselected": "Unselected",
    "Unlocked": "Unlocked",
    "Locked": "Locked"
}
lolEventHubOfferCategories: dict[str, str] = {
    "Currencies": "Currency",
    "Tft": "TFT",
    "Loot": "Loot",
    "Borders": "Border",
    "Skins": "Skin",
    "Chromas": "Chroma",
    "Featured": "Featured"
}
cardSizes: dict[str, str] = {
    "kDefault": "default",
    "kLarge": "large"
}
lolEventHubRewardTrackItemHeaderTypes: dict[str, str] = {
    "NONE": "NONE",
    "FREE": "FREE",
    "PREMIUM": "PREMIUM",
}
lolEventHubOfferStates: dict[str, str] = {
    "kPurchasing": "kPurchasing",
    "kUnrevealed": "kUnrevealed",
    "kUnavailable": "kUnavailable",
    "kAvailable": "kAvailable",
    "kOwned": "kOwned"
}
#进度（Progression）
counterDirections: dict[str, str] = {
    "INCREASING": "INCREASING"
}
milestone_triggerRequirements: dict[str, str] = {
    "": "",
    "ALL": "ALL"
}
milestoneSizes: dict[str, str] = {
    "kLarge": "kLarge"
}
milestoneTriggerTypes: dict[str, str] = {
    "COUNTER": "COUNTER",
    "ENTITLEMENT_ITEM_ID": "ENTITLEMENT_ITEM_ID"
}
