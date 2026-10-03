import random
import time
import json
from datetime import datetime, timedelta

MEMBERSHIP_PRICE = 288.88
NORMAL_MAX_PLAYS = 5
MEMBER_MAX_PLAYS = 10
MEMBER_BONUS_RATE = 0.30

MEMBERSHIP_TIERS = {
    'none': {'name': '普通用户', 'price': 0, 'max_plays': 5, 'bonus_rate': 0.0, 'daily_task_bonus': 0, 'exclusive_games': [], 'duration_days': 0, 'auto_renew': False, 'renew_discount': 1.0, 'drop_multiplier': 1.0},
    'normal': {'name': '普通会员', 'price': 288.88, 'max_plays': 10, 'bonus_rate': 0.30, 'daily_task_bonus': 0, 'exclusive_games': [], 'duration_days': 7, 'auto_renew': True, 'renew_discount': 0.9, 'drop_multiplier': 1.2},
    'gold': {'name': '黄金会员', 'price': 588.88, 'max_plays': 15, 'bonus_rate': 0.50, 'daily_task_bonus': 5, 'exclusive_games': ['lucky_wheel', 'dice_royale'], 'duration_days': 15, 'auto_renew': True, 'renew_discount': 0.9, 'drop_multiplier': 1.5},
    'diamond': {'name': '钻石会员', 'price': 1288.88, 'max_plays': 50, 'bonus_rate': 1.00, 'daily_task_bonus': 10, 'exclusive_games': ['lucky_wheel', 'memory_cards', 'dice_royale', 'blackjack_tournament'], 'duration_days': 30, 'auto_renew': True, 'renew_discount': 0.9, 'drop_multiplier': 2.0},
    'supreme': {'name': '至尊会员', 'price': 12888.00, 'max_plays': 80, 'bonus_rate': 3.00, 'daily_task_bonus': 30, 'exclusive_games': ['lucky_wheel', 'memory_cards', 'dice_royale', 'blackjack_tournament', 'treasure_hunt', 'boss_battle'], 'requirements': {'min_total_plays': 180, 'min_win_rate': 72.0}, 'duration_days': 30, 'auto_renew': True, 'renew_discount': 0.9, 'drop_multiplier': 3.0},
    'normal_lifetime': {'name': '普通会员(永久)', 'price': 1888.88, 'max_plays': 10, 'bonus_rate': 0.30, 'daily_task_bonus': 0, 'exclusive_games': [], 'duration_days': 0, 'auto_renew': False, 'renew_discount': 1.0, 'drop_multiplier': 1.2},
    'gold_lifetime': {'name': '黄金会员(永久)', 'price': 3888.88, 'max_plays': 15, 'bonus_rate': 0.50, 'daily_task_bonus': 5, 'exclusive_games': ['lucky_wheel', 'dice_royale'], 'duration_days': 0, 'auto_renew': False, 'renew_discount': 1.0, 'drop_multiplier': 1.5},
    'diamond_lifetime': {'name': '钻石会员(永久)', 'price': 8888.88, 'max_plays': 50, 'bonus_rate': 1.00, 'daily_task_bonus': 10, 'exclusive_games': ['lucky_wheel', 'memory_cards', 'dice_royale', 'blackjack_tournament'], 'duration_days': 0, 'auto_renew': False, 'renew_discount': 1.0, 'drop_multiplier': 2.0},
}

GAME_NAME_MAP = {
    'dice': '骰子大战',
    'blackjack': '二十一点',
    'guess_number': '猜数字',
    'rock_paper_scissors': '石头剪刀布',
    'roulette': '轮盘赌',
    'whack_mole': '打地鼠',
    'lucky_wheel': '幸运转盘',
    'memory_cards': '记忆翻牌',
    'dice_royale': '骰子王者',
    'blackjack_tournament': '21点锦标赛',
    'treasure_hunt': '寻宝迷宫',
    'boss_battle': '挑战BOSS'
}

LEVEL_SYSTEM = {
    'levels': [
        {'level': 1, 'name': '新手', 'icon': '🌱', 'min_points': 0, 'min_wins': 0, 'min_plays': 0},
        {'level': 5, 'name': '学徒', 'icon': '🌿', 'min_points': 50, 'min_wins': 10, 'min_plays': 30},
        {'level': 10, 'name': '熟练', 'icon': '🍀', 'min_points': 200, 'min_wins': 30, 'min_plays': 100},
        {'level': 20, 'name': '精英', 'icon': '⭐', 'min_points': 800, 'min_wins': 80, 'min_plays': 300},
        {'level': 30, 'name': '大师', 'icon': '🌟', 'min_points': 2000, 'min_wins': 150, 'min_plays': 600},
        {'level': 50, 'name': '宗师', 'icon': '💫', 'min_points': 5000, 'min_wins': 300, 'min_plays': 1200},
        {'level': 80, 'name': '传奇', 'icon': '👑', 'min_points': 15000, 'min_wins': 600, 'min_plays': 2500},
        {'level': 100, 'name': '神话', 'icon': '🔱', 'min_points': 50000, 'min_wins': 1200, 'min_plays': 5000}
    ]
}

TITLE_SYSTEM = {
    'titles': [
        {'id': 'novice', 'name': '初出茅庐', 'icon': '🐣', 'condition_type': 'total_plays', 'condition_value': 1},
        {'id': 'dice_lover', 'name': '骰子爱好者', 'icon': '🎲', 'condition_type': 'game_plays_dice', 'condition_value': 30},
        {'id': 'dice_king', 'name': '骰子王', 'icon': '🎲', 'condition_type': 'game_wins_dice', 'condition_value': 50},
        {'id': 'bj_master', 'name': '21点大师', 'icon': '🃏', 'condition_type': 'game_wins_blackjack', 'condition_value': 30},
        {'id': 'guess_expert', 'name': '猜数字专家', 'icon': '🎯', 'condition_type': 'game_wins_guess_number', 'condition_value': 30},
        {'id': 'rps_champ', 'name': '出拳冠军', 'icon': '🤖', 'condition_type': 'game_wins_rock_paper_scissors', 'condition_value': 30},
        {'id': 'roulette_god', 'name': '赌神', 'icon': '🎡', 'condition_type': 'game_wins_roulette', 'condition_value': 30},
        {'id': 'whack_hunter', 'name': '地鼠猎人', 'icon': '🔨', 'condition_type': 'game_wins_whack_mole', 'condition_value': 30},
        {'id': 'wheel_spinner', 'name': '转盘高手', 'icon': '🎰', 'condition_type': 'game_wins_lucky_wheel', 'condition_value': 20},
        {'id': 'memory_keeper', 'name': '记忆守护者', 'icon': '🧠', 'condition_type': 'game_wins_memory_cards', 'condition_value': 20},
        {'id': 'dice_royale_master', 'name': '骰子王者', 'icon': '👑', 'condition_type': 'game_wins_dice_royale', 'condition_value': 20},
        {'id': 'tournament_champ', 'name': '锦标赛冠军', 'icon': '🏆', 'condition_type': 'game_wins_blackjack_tournament', 'condition_value': 10},
        {'id': 'treasure_hunter', 'name': '寻宝猎人', 'icon': '💎', 'condition_type': 'game_wins_treasure_hunt', 'condition_value': 15},
        {'id': 'boss_slayer', 'name': 'BOSS终结者', 'icon': '⚔️', 'condition_type': 'game_wins_boss_battle', 'condition_value': 10},
        {'id': 'streak_3', 'name': '三连胜', 'icon': '🔥', 'condition_type': 'max_win_streak', 'condition_value': 3},
        {'id': 'streak_5', 'name': '五连胜', 'icon': '🔥', 'condition_type': 'max_win_streak', 'condition_value': 5},
        {'id': 'streak_10', 'name': '十连胜', 'icon': '⚡', 'condition_type': 'max_win_streak', 'condition_value': 10},
        {'id': 'play_100', 'name': '百战老兵', 'icon': '⚔️', 'condition_type': 'total_plays', 'condition_value': 100},
        {'id': 'play_500', 'name': '游戏狂人', 'icon': '👑', 'condition_type': 'total_plays', 'condition_value': 500},
        {'id': 'win_100', 'name': '百胜将军', 'icon': '🎖️', 'condition_type': 'total_wins', 'condition_value': 100},
        {'id': 'collector', 'name': '卡牌收藏家', 'icon': '📖', 'condition_type': 'cards_total', 'condition_value': 30},
        {'id': 'member_gold', 'name': '黄金尊享', 'icon': '🥇', 'condition_type': 'tier', 'condition_value': 'gold'},
        {'id': 'member_diamond', 'name': '钻石尊享', 'icon': '💎', 'condition_type': 'tier', 'condition_value': 'diamond'},
        {'id': 'member_supreme', 'name': '至尊荣耀', 'icon': '👑', 'condition_type': 'tier', 'condition_value': 'supreme'},
        {'id': 'lucky_star', 'name': '天选之子', 'icon': '🌟', 'condition_type': 'lucky_x20', 'condition_value': 1},
        {'id': 'gcoin_collector', 'name': 'G币收藏家', 'icon': '🪙', 'condition_type': 'gcoins_total', 'condition_value': 10000},
        {'id': 'market_trader', 'name': '交易达人', 'icon': '📈', 'condition_type': 'market_trades', 'condition_value': 10},
        {'id': 'auction_winner', 'name': '拍卖赢家', 'icon': '🔨', 'condition_type': 'auction_wins', 'condition_value': 5}
    ]
}

DAILY_TASK_POOL = [
    {'id': 'play_3', 'name': '玩3局任意游戏', 'target': 3, 'reward': 5, 'type': 'play_count'},
    {'id': 'win_2', 'name': '赢得2局游戏', 'target': 2, 'reward': 6, 'type': 'win_count'},
    {'id': 'play_dice', 'name': '玩1局骰子大战', 'target': 1, 'reward': 4, 'type': 'game_specific', 'game': 'dice'},
    {'id': 'play_blackjack', 'name': '玩1局二十一点', 'target': 1, 'reward': 4, 'type': 'game_specific', 'game': 'blackjack'},
    {'id': 'play_guess', 'name': '玩1局猜数字', 'target': 1, 'reward': 4, 'type': 'game_specific', 'game': 'guess_number'},
    {'id': 'play_rps', 'name': '玩1局石头剪刀布', 'target': 1, 'reward': 4, 'type': 'game_specific', 'game': 'rock_paper_scissors'},
    {'id': 'play_roulette', 'name': '玩1局轮盘赌', 'target': 1, 'reward': 5, 'type': 'game_specific', 'game': 'roulette'},
    {'id': 'play_whack', 'name': '玩1局打地鼠', 'target': 1, 'reward': 4, 'type': 'game_specific', 'game': 'whack_mole'},
    {'id': 'win_streak_2', 'name': '连赢2局', 'target': 2, 'reward': 8, 'type': 'win_streak'},
    {'id': 'guess_win_fast', 'name': '猜数字5次内猜中', 'target': 1, 'reward': 8, 'type': 'guess_fast'},
    {'id': 'roulette_win', 'name': '轮盘赌赢一次', 'target': 1, 'reward': 6, 'type': 'roulette_win'},
    {'id': 'play_dice_royale', 'name': '玩1局骰子王者', 'target': 1, 'reward': 8, 'type': 'game_specific', 'game': 'dice_royale'},
    {'id': 'play_tournament', 'name': '玩1局21点锦标赛', 'target': 1, 'reward': 8, 'type': 'game_specific', 'game': 'blackjack_tournament'},
    {'id': 'play_treasure', 'name': '玩1局寻宝迷宫', 'target': 1, 'reward': 10, 'type': 'game_specific', 'game': 'treasure_hunt'},
    {'id': 'play_boss', 'name': '挑战1次BOSS', 'target': 1, 'reward': 12, 'type': 'game_specific', 'game': 'boss_battle'}
]

ACHIEVEMENTS = [
    {'id': 'first_game', 'name': '初出茅庐', 'desc': '玩第一局游戏', 'icon': '🎖️', 'reward': 2, 'type': 'total_plays', 'target': 1},
    {'id': 'play_10', 'name': '游戏新手', 'desc': '累计玩10局游戏', 'icon': '🎮', 'reward': 5, 'type': 'total_plays', 'target': 10},
    {'id': 'play_50', 'name': '游戏达人', 'desc': '累计玩50局游戏', 'icon': '🕹️', 'reward': 15, 'type': 'total_plays', 'target': 50},
    {'id': 'play_100', 'name': '百战老兵', 'desc': '累计玩100局游戏', 'icon': '⚔️', 'reward': 30, 'type': 'total_plays', 'target': 100},
    {'id': 'play_500', 'name': '游戏狂人', 'desc': '累计玩500局游戏', 'icon': '👑', 'reward': 100, 'type': 'total_plays', 'target': 500},
    {'id': 'win_10', 'name': '小有所成', 'desc': '累计赢得10局游戏', 'icon': '🏅', 'reward': 5, 'type': 'total_wins', 'target': 10},
    {'id': 'win_50', 'name': '胜利达人', 'desc': '累计赢得50局游戏', 'icon': '🏆', 'reward': 20, 'type': 'total_wins', 'target': 50},
    {'id': 'win_100', 'name': '百胜将军', 'desc': '累计赢得100局游戏', 'icon': '🎯', 'reward': 40, 'type': 'total_wins', 'target': 100},
    {'id': 'win_500', 'name': '常胜将军', 'desc': '累计赢得500局游戏', 'icon': '💎', 'reward': 150, 'type': 'total_wins', 'target': 500},
    {'id': 'streak_5', 'name': '五连胜', 'desc': '达成5连胜', 'icon': '🔥', 'reward': 15, 'type': 'max_win_streak', 'target': 5},
    {'id': 'streak_10', 'name': '十连胜', 'desc': '达成10连胜', 'icon': '⚡', 'reward': 50, 'type': 'max_win_streak', 'target': 10},
    {'id': 'dice_master', 'name': '骰子大师', 'desc': '骰子大战获胜20次', 'icon': '🎲', 'reward': 20, 'type': 'game_wins_dice', 'target': 20},
    {'id': 'blackjack_master', 'name': '21点高手', 'desc': '二十一点获胜20次', 'icon': '🃏', 'reward': 20, 'type': 'game_wins_blackjack', 'target': 20},
    {'id': 'guess_master', 'name': '猜数字达人', 'desc': '猜数字获胜20次', 'icon': '🎯', 'reward': 20, 'type': 'game_wins_guess_number', 'target': 20},
    {'id': 'rps_master', 'name': '石头剪刀布宗师', 'desc': '石头剪刀布获胜20次', 'icon': '🤖', 'reward': 20, 'type': 'game_wins_rock_paper_scissors', 'target': 20},
    {'id': 'roulette_master', 'name': '轮盘赌赌神', 'desc': '轮盘赌获胜20次', 'icon': '🎡', 'reward': 25, 'type': 'game_wins_roulette', 'target': 20},
    {'id': 'whack_master', 'name': '打地鼠达人', 'desc': '打地鼠获胜20次', 'icon': '🔨', 'reward': 20, 'type': 'game_wins_whack_mole', 'target': 20},
    {'id': 'dice_god', 'name': '骰子之神', 'desc': '骰子大战获胜100次', 'icon': '🎲', 'reward': 80, 'type': 'game_wins_dice', 'target': 100},
    {'id': 'roulette_god', 'name': '赌神', 'desc': '轮盘赌猜中数字10次', 'icon': '🎰', 'reward': 100, 'type': 'roulette_number_hits', 'target': 10},
    {'id': 'memory_king', 'name': '记忆之王', 'desc': '记忆翻牌15步内完成3次', 'icon': '🧠', 'reward': 80, 'type': 'memory_perfect', 'target': 3},
    {'id': 'points_1000', 'name': '千金散尽', 'desc': '累计赚取1000积分', 'icon': '💰', 'reward': 30, 'type': 'total_points_earned', 'target': 1000},
    {'id': 'points_10000', 'name': '万贯家财', 'desc': '累计赚取10000积分', 'icon': '💎', 'reward': 100, 'type': 'total_points_earned', 'target': 10000},
    {'id': 'member_bronze', 'name': '会员之路', 'desc': '开通任意会员', 'icon': '👑', 'reward': 10, 'type': 'is_member', 'target': 1},
    {'id': 'member_diamond', 'name': '钻石尊享', 'desc': '成为钻石会员', 'icon': '💎', 'reward': 50, 'type': 'is_diamond', 'target': 1},
    {'id': 'member_gold', 'name': '黄金尊享', 'desc': '成为黄金会员', 'icon': '🥇', 'reward': 30, 'type': 'is_gold', 'target': 1},
    {'id': 'member_supreme', 'name': '至尊荣耀', 'desc': '成为至尊会员', 'icon': '👑', 'reward': 200, 'type': 'is_supreme', 'target': 1},
    {'id': 'hidden_lucky', 'name': '天选之子', 'desc': '幸运转盘抽中x20', 'icon': '🌟', 'reward': 88, 'type': 'lucky_x20', 'target': 1},
    {'id': 'hidden_lose_streak', 'name': '屡败屡战', 'desc': '达成连败5局', 'icon': '💪', 'reward': 10, 'type': 'max_lose_streak', 'target': 5},
    {'id': 'login_7', 'name': '七日之约', 'desc': '连续签到7天', 'icon': '📅', 'reward': 15, 'type': 'checkin_streak', 'target': 7},
    {'id': 'checkin_30', 'name': '月满勤', 'desc': '累计签到30天', 'icon': '📆', 'reward': 50, 'type': 'checkin_total', 'target': 30},
    {'id': 'chest_all', 'name': '宝箱猎人', 'desc': '开启全部5个活跃宝箱', 'icon': '🧰', 'reward': 20, 'type': 'chest_full', 'target': 1},
    {'id': 'first_win_daily', 'name': '开门红', 'desc': '领取首次每日首胜', 'icon': '🌅', 'reward': 5, 'type': 'daily_first_win', 'target': 1},
    {'id': 'collect_first', 'name': '收藏家', 'desc': '收集第一张卡牌', 'icon': '📖', 'reward': 3, 'type': 'cards_total', 'target': 1},
    {'id': 'collect_10', 'name': '卡牌新手', 'desc': '收集10张不同卡牌', 'icon': '🃏', 'reward': 10, 'type': 'cards_total', 'target': 10},
    {'id': 'collect_30', 'name': '卡牌大师', 'desc': '收集30张不同卡牌', 'icon': '🎴', 'reward': 50, 'type': 'cards_total', 'target': 30},
    {'id': 'collect_all', 'name': '图鉴全收', 'desc': '收集全部卡牌', 'icon': '🏅', 'reward': 200, 'type': 'cards_total', 'target': 75},
    {'id': 'collect_set_dice', 'name': '骰子收藏', 'desc': '集齐骰子大战卡牌', 'icon': '🎲', 'reward': 30, 'type': 'cards_set_dice', 'target': 1},
    {'id': 'collect_set_blackjack', 'name': '扑克收藏', 'desc': '集齐二十一点卡牌', 'icon': '🃏', 'reward': 40, 'type': 'cards_set_blackjack', 'target': 1},
    {'id': 'collect_set_guess', 'name': '数字收藏', 'desc': '集齐猜数字卡牌', 'icon': '🎯', 'reward': 35, 'type': 'cards_set_guess_number', 'target': 1},
    {'id': 'collect_set_rps', 'name': '手势收藏', 'desc': '集齐石头剪刀布卡牌', 'icon': '🤖', 'reward': 25, 'type': 'cards_set_rock_paper_scissors', 'target': 1},
    {'id': 'collect_set_roulette', 'name': '轮盘收藏', 'desc': '集齐轮盘赌卡牌', 'icon': '🎡', 'reward': 35, 'type': 'cards_set_roulette', 'target': 1},
    {'id': 'collect_set_wheel', 'name': '转盘收藏', 'desc': '集齐幸运转盘卡牌', 'icon': '🎰', 'reward': 35, 'type': 'cards_set_lucky_wheel', 'target': 1},
    {'id': 'collect_set_memory', 'name': '记忆收藏', 'desc': '集齐记忆翻牌卡牌', 'icon': '🧠', 'reward': 35, 'type': 'cards_set_memory_cards', 'target': 1},
    {'id': 'whack_perfect', 'name': '打地鼠之神', 'desc': '打地鼠得分30', 'icon': '🔨', 'reward': 30, 'type': 'whack_score_30', 'target': 1},
    {'id': 'coupon_collector', 'name': '优惠券猎人', 'desc': '累计获得5张会员优惠券', 'icon': '🎟️', 'reward': 25, 'type': 'membership_coupon_count', 'target': 5},
    {'id': 'coupon_use', 'name': '精打细算', 'desc': '使用会员优惠券开通会员', 'icon': '💳', 'reward': 15, 'type': 'membership_coupon_used', 'target': 1},
    {'id': 'dice_royale_ace', 'name': '骰子王者', 'desc': '骰子王者获胜20次', 'icon': '👑', 'reward': 60, 'type': 'game_wins_dice_royale', 'target': 20},
    {'id': 'tournament_king', 'name': '锦标赛之王', 'desc': '21点锦标赛获胜10次', 'icon': '🏆', 'reward': 100, 'type': 'game_wins_blackjack_tournament', 'target': 10},
    {'id': 'treasure_master', 'name': '寻宝大师', 'desc': '寻宝迷宫获胜15次', 'icon': '💎', 'reward': 80, 'type': 'game_wins_treasure_hunt', 'target': 15},
    {'id': 'boss_slayer', 'name': 'BOSS终结者', 'desc': '击败BOSS 10次', 'icon': '⚔️', 'reward': 150, 'type': 'game_wins_boss_battle', 'target': 10},
    {'id': 'gcoin_1000', 'name': 'G币新手', 'desc': '累计获得1000 G币', 'icon': '🪙', 'reward': 20, 'type': 'gcoins_total', 'target': 1000},
    {'id': 'gcoin_10000', 'name': 'G币大户', 'desc': '累计获得10000 G币', 'icon': '💰', 'reward': 100, 'type': 'gcoins_total', 'target': 10000},
    {'id': 'gcoin_100000', 'name': 'G币巨富', 'desc': '累计获得100000 G币', 'icon': '💎', 'reward': 500, 'type': 'gcoins_total', 'target': 100000},
    {'id': 'market_first_trade', 'name': '初次交易', 'desc': '完成第一笔卡牌交易', 'icon': '📈', 'reward': 10, 'type': 'market_trades', 'target': 1},
    {'id': 'market_10_trades', 'name': '交易达人', 'desc': '完成10笔卡牌交易', 'icon': '💹', 'reward': 50, 'type': 'market_trades', 'target': 10},
    {'id': 'market_50_trades', 'name': '交易大师', 'desc': '完成50笔卡牌交易', 'icon': '🏦', 'reward': 200, 'type': 'market_trades', 'target': 50},
    {'id': 'auction_first_win', 'name': '初次竞拍', 'desc': '赢得第一次拍卖', 'icon': '🔨', 'reward': 20, 'type': 'auction_wins', 'target': 1},
    {'id': 'auction_5_wins', 'name': '拍卖行家', 'desc': '赢得5次拍卖', 'icon': '⚖️', 'reward': 80, 'type': 'auction_wins', 'target': 5},
    {'id': 'auction_20_wins', 'name': '拍卖之王', 'desc': '赢得20次拍卖', 'icon': '👑', 'reward': 300, 'type': 'auction_wins', 'target': 20}
]

ITEM_SHOP = {
    'lucky_charm': {'id': 'lucky_charm', 'name': '幸运符', 'icon': '🍀', 'desc': '本局胜率+5%（游戏开始前使用）', 'price': 5, 'duration': 300, 'games': ['dice', 'blackjack', 'roulette'], 'member_only': False, 'min_tier': 'none'},
    'double_card': {'id': 'double_card', 'name': '双倍卡', 'icon': '✨', 'desc': '本局G币翻倍（游戏开始前使用）', 'price': 15, 'duration': 300, 'games': [], 'member_only': False, 'min_tier': 'none'},
    'amulet': {'id': 'amulet', 'name': '护身符', 'icon': '🛡️', 'desc': '本局输了不扣次数（游戏开始前使用）', 'price': 10, 'duration': 300, 'games': [], 'member_only': False, 'min_tier': 'none'},
    'scope': {'id': 'scope', 'name': '瞄准镜', 'icon': '🎯', 'desc': '打地鼠时间+10秒', 'price': 20, 'duration': 300, 'games': ['whack_mole'], 'member_only': False, 'min_tier': 'none'},
    'triple_card': {'id': 'triple_card', 'name': 'G币三倍卡', 'icon': '💎', 'desc': '本局G币 ×3（比双倍卡更划算）', 'price': 50, 'duration': 300, 'games': [], 'member_only': False, 'min_tier': 'none'},
    'extra_play': {'id': 'extra_play', 'name': '免费次数券', 'icon': '🎟️', 'desc': '立即增加今日游戏次数+1（可叠加，最多5次）', 'price': 40, 'duration': 0, 'games': [], 'member_only': False, 'min_tier': 'none'},
    'insurance': {'id': 'insurance', 'name': '保险券', 'icon': '📄', 'desc': '本局失败返还50%消耗的G币（游戏开始前使用）', 'price': 12, 'duration': 300, 'games': [], 'member_only': False, 'min_tier': 'none'},
    'reroll': {'id': 'reroll', 'name': '重投卡', 'icon': '🔄', 'desc': '骰子大战/二十一点可重投一次（游戏开始前使用）', 'price': 18, 'duration': 300, 'games': ['dice', 'blackjack'], 'member_only': False, 'min_tier': 'none'},
    'member_lucky_charm': {'id': 'member_lucky_charm', 'name': '会员幸运符', 'icon': '🍀', 'desc': '本局胜率+15%（会员专属）', 'price': 15, 'duration': 300, 'games': ['dice', 'blackjack', 'roulette'], 'member_only': True, 'min_tier': 'gold'},
    'member_revive': {'id': 'member_revive', 'name': '会员复活卡', 'icon': '💫', 'desc': '输掉后立即重玩一次，不消耗次数（会员专属）', 'price': 30, 'duration': 0, 'games': [], 'member_only': True, 'min_tier': 'diamond'},
    'member_double_drop': {'id': 'member_double_drop', 'name': '卡牌双倍掉落', 'icon': '🃏', 'desc': '本局卡牌掉落概率翻倍（会员专属）', 'price': 25, 'duration': 300, 'games': [], 'member_only': True, 'min_tier': 'gold'},
    'member_double_coupon': {'id': 'member_double_coupon', 'name': '优惠券双倍掉落', 'icon': '🎟️', 'desc': '本局会员优惠券掉落概率翻倍（会员专属）', 'price': 20, 'duration': 300, 'games': [], 'member_only': True, 'min_tier': 'gold'},
}

CHECKIN_REWARDS = [
    {'day': 1, 'reward_type': 'points', 'value': 3.0, 'icon': '💧', 'desc': '3积分'},
    {'day': 2, 'reward_type': 'points', 'value': 8.0, 'icon': '💧', 'desc': '8积分'},
    {'day': 3, 'reward_type': 'point_code', 'value': 1, 'icon': '🎫', 'desc': '普通积分卡密 x1'},
    {'day': 4, 'reward_type': 'points', 'value': 6.0, 'icon': '💧', 'desc': '6积分'},
    {'day': 5, 'reward_type': 'boost_code', 'value': 1, 'icon': '⚡', 'desc': '积分加成卡 x1'},
    {'day': 6, 'reward_type': 'points', 'value': 9.0, 'icon': '💰', 'desc': '9积分'},
    {'day': 7, 'reward_type': 'premium_point_code', 'value': 1, 'icon': '💎', 'desc': '高级积分卡密 x1'}
]

CHEST_REWARDS = [
    {'plays': 1, 'name': '青铜宝箱', 'icon': '🥉', 'points_min': 1, 'points_max': 3, 'item_chance': 0, 'gcoin_min': 0, 'gcoin_max': 0},
    {'plays': 3, 'name': '白银宝箱', 'icon': '🥈', 'points_min': 3, 'points_max': 6, 'item_chance': 0, 'gcoin_min': 5, 'gcoin_max': 15},
    {'plays': 5, 'name': '黄金宝箱', 'icon': '🥇', 'points_min': 6, 'points_max': 12, 'item_chance': 0.1, 'gcoin_min': 20, 'gcoin_max': 50},
    {'plays': 10, 'name': '钻石宝箱', 'icon': '💎', 'points_min': 15, 'points_max': 30, 'item_chance': 0.3, 'gcoin_min': 60, 'gcoin_max': 120},
    {'plays': 20, 'name': '传说宝箱', 'icon': '👑', 'points_min': 50, 'points_max': 80, 'item_chance': 1.0, 'gcoin_min': 200, 'gcoin_max': 500}
]

CARD_COLLECTIONS = {
    'dice': {'name': '骰子大战', 'icon': '🎲', 'cards': [
        {'id': 'd1', 'name': '一点', 'emoji': '⚀', 'rarity': 'common'},
        {'id': 'd2', 'name': '二点', 'emoji': '⚁', 'rarity': 'common'},
        {'id': 'd3', 'name': '三点', 'emoji': '⚂', 'rarity': 'common'},
        {'id': 'd4', 'name': '四点', 'emoji': '⚃', 'rarity': 'rare'},
        {'id': 'd5', 'name': '五点', 'emoji': '⚄', 'rarity': 'rare'},
        {'id': 'd6', 'name': '六点', 'emoji': '⚅', 'rarity': 'epic'}
    ]},
    'blackjack': {'name': '二十一点', 'icon': '🃏', 'cards': [
        {'id': 'bj_A', 'name': 'A', 'emoji': '🅰️', 'rarity': 'epic'},
        {'id': 'bj_2', 'name': '2', 'emoji': '2️⃣', 'rarity': 'common'},
        {'id': 'bj_3', 'name': '3', 'emoji': '3️⃣', 'rarity': 'common'},
        {'id': 'bj_4', 'name': '4', 'emoji': '4️⃣', 'rarity': 'common'},
        {'id': 'bj_5', 'name': '5', 'emoji': '5️⃣', 'rarity': 'common'},
        {'id': 'bj_6', 'name': '6', 'emoji': '6️⃣', 'rarity': 'common'},
        {'id': 'bj_7', 'name': '7', 'emoji': '7️⃣', 'rarity': 'common'},
        {'id': 'bj_8', 'name': '8', 'emoji': '8️⃣', 'rarity': 'rare'},
        {'id': 'bj_9', 'name': '9', 'emoji': '9️⃣', 'rarity': 'rare'},
        {'id': 'bj_10', 'name': '10', 'emoji': '🔟', 'rarity': 'rare'},
        {'id': 'bj_J', 'name': 'J', 'emoji': '🇯', 'rarity': 'epic'},
        {'id': 'bj_Q', 'name': 'Q', 'emoji': '🇶', 'rarity': 'epic'},
        {'id': 'bj_K', 'name': 'K', 'emoji': '🇰', 'rarity': 'legendary'}
    ]},
    'guess_number': {'name': '猜数字', 'icon': '🎯', 'cards': [
        {'id': 'g0', 'name': '0', 'emoji': '0️⃣', 'rarity': 'common'},
        {'id': 'g1', 'name': '1', 'emoji': '1️⃣', 'rarity': 'common'},
        {'id': 'g2', 'name': '2', 'emoji': '2️⃣', 'rarity': 'common'},
        {'id': 'g3', 'name': '3', 'emoji': '3️⃣', 'rarity': 'common'},
        {'id': 'g4', 'name': '4', 'emoji': '4️⃣', 'rarity': 'common'},
        {'id': 'g5', 'name': '5', 'emoji': '5️⃣', 'rarity': 'common'},
        {'id': 'g6', 'name': '6', 'emoji': '6️⃣', 'rarity': 'rare'},
        {'id': 'g7', 'name': '7', 'emoji': '7️⃣', 'rarity': 'rare'},
        {'id': 'g8', 'name': '8', 'emoji': '8️⃣', 'rarity': 'epic'},
        {'id': 'g9', 'name': '9', 'emoji': '9️⃣', 'rarity': 'legendary'}
    ]},
    'rock_paper_scissors': {'name': '石头剪刀布', 'icon': '🤖', 'cards': [
        {'id': 'rps_rock', 'name': '石头', 'emoji': '🪨', 'rarity': 'common'},
        {'id': 'rps_paper', 'name': '布', 'emoji': '📄', 'rarity': 'common'},
        {'id': 'rps_scissors', 'name': '剪刀', 'emoji': '✂️', 'rarity': 'rare'}
    ]},
    'roulette': {'name': '轮盘赌', 'icon': '🎡', 'cards': [
        {'id': 'r_red', 'name': '红色', 'emoji': '🔴', 'rarity': 'common'},
        {'id': 'r_black', 'name': '黑色', 'emoji': '⚫', 'rarity': 'common'},
        {'id': 'r_green', 'name': '绿色', 'emoji': '🟢', 'rarity': 'legendary'},
        {'id': 'r_even', 'name': '偶数', 'emoji': '2️⃣', 'rarity': 'rare'},
        {'id': 'r_odd', 'name': '奇数', 'emoji': '1️⃣', 'rarity': 'rare'},
        {'id': 'r_high', 'name': '大数', 'emoji': '⬆️', 'rarity': 'rare'},
        {'id': 'r_low', 'name': '小数', 'emoji': '⬇️', 'rarity': 'rare'},
        {'id': 'r_zero', 'name': '0', 'emoji': '0️⃣', 'rarity': 'epic'}
    ]},
    'lucky_wheel': {'name': '幸运转盘', 'icon': '🎰', 'cards': [
        {'id': 'w_pass', 'name': '谢谢参与', 'emoji': '🙏', 'rarity': 'common'},
        {'id': 'w_x1', 'name': 'x1', 'emoji': '1️⃣', 'rarity': 'common'},
        {'id': 'w_x2', 'name': 'x2', 'emoji': '2️⃣', 'rarity': 'common'},
        {'id': 'w_x3', 'name': 'x3', 'emoji': '3️⃣', 'rarity': 'rare'},
        {'id': 'w_x5', 'name': 'x5', 'emoji': '5️⃣', 'rarity': 'rare'},
        {'id': 'w_x8', 'name': 'x8', 'emoji': '8️⃣', 'rarity': 'epic'},
        {'id': 'w_x10', 'name': 'x10', 'emoji': '🔟', 'rarity': 'epic'},
        {'id': 'w_x20', 'name': 'x20', 'emoji': '💫', 'rarity': 'legendary'}
    ]},
    'memory_cards': {'name': '记忆翻牌', 'icon': '🧠', 'cards': [
        {'id': 'm_apple', 'name': '苹果', 'emoji': '🍎', 'rarity': 'common'},
        {'id': 'm_banana', 'name': '香蕉', 'emoji': '🍌', 'rarity': 'common'},
        {'id': 'm_grape', 'name': '葡萄', 'emoji': '🍇', 'rarity': 'common'},
        {'id': 'm_strawberry', 'name': '草莓', 'emoji': '🍓', 'rarity': 'rare'},
        {'id': 'm_cherry', 'name': '樱桃', 'emoji': '🍒', 'rarity': 'rare'},
        {'id': 'm_peach', 'name': '桃子', 'emoji': '🍑', 'rarity': 'epic'},
        {'id': 'm_kiwi', 'name': '猕猴桃', 'emoji': '🥝', 'rarity': 'epic'},
        {'id': 'm_pineapple', 'name': '菠萝', 'emoji': '🍍', 'rarity': 'legendary'}
    ]},
    'whack_mole': {'name': '打地鼠', 'icon': '🔨', 'cards': [
        {'id': 'wm_mole', 'name': '地鼠', 'emoji': '🐹', 'rarity': 'common'},
        {'id': 'wm_bomb', 'name': '炸弹', 'emoji': '💣', 'rarity': 'legendary'}
    ]},
    'dice_royale': {'name': '骰子王者', 'icon': '👑', 'cards': [
        {'id': 'dr_bronze', 'name': '青铜骰', 'emoji': '🥉', 'rarity': 'common'},
        {'id': 'dr_silver', 'name': '白银骰', 'emoji': '🥈', 'rarity': 'rare'},
        {'id': 'dr_gold', 'name': '黄金骰', 'emoji': '🥇', 'rarity': 'epic'},
        {'id': 'dr_diamond', 'name': '钻石骰', 'emoji': '💎', 'rarity': 'legendary'},
        {'id': 'dr_crown', 'name': '王者骰', 'emoji': '👑', 'rarity': 'legendary'}
    ]},
    'blackjack_tournament': {'name': '21点锦标赛', 'icon': '🏆', 'cards': [
        {'id': 'bt_bronze', 'name': '青铜奖杯', 'emoji': '🥉', 'rarity': 'common'},
        {'id': 'bt_silver', 'name': '白银奖杯', 'emoji': '🥈', 'rarity': 'rare'},
        {'id': 'bt_gold', 'name': '黄金奖杯', 'emoji': '🥇', 'rarity': 'epic'},
        {'id': 'bt_crown', 'name': '王者奖杯', 'emoji': '👑', 'rarity': 'legendary'}
    ]},
    'treasure_hunt': {'name': '寻宝迷宫', 'icon': '💎', 'cards': [
        {'id': 'th_coin', 'name': '金币', 'emoji': '🪙', 'rarity': 'common'},
        {'id': 'th_gem', 'name': '宝石', 'emoji': '💎', 'rarity': 'rare'},
        {'id': 'th_crown', 'name': '王冠', 'emoji': '👑', 'rarity': 'epic'},
        {'id': 'th_relic', 'name': '远古遗物', 'emoji': '🏺', 'rarity': 'legendary'}
    ]},
    'boss_battle': {'name': '挑战BOSS', 'icon': '⚔️', 'cards': [
        {'id': 'bb_slime', 'name': '史莱姆', 'emoji': '🟢', 'rarity': 'common'},
        {'id': 'bb_wolf', 'name': '狼王', 'emoji': '🐺', 'rarity': 'rare'},
        {'id': 'bb_dragon', 'name': '巨龙', 'emoji': '🐲', 'rarity': 'epic'},
        {'id': 'bb_demon', 'name': '魔王', 'emoji': '👹', 'rarity': 'legendary'}
    ]}
}

CARD_RARITY_NAMES = {'common': '普通', 'rare': '稀有', 'epic': '史诗', 'legendary': '传说'}
CARD_RARITY_COLORS = {'common': '#9ca3af', 'rare': '#60a5fa', 'epic': '#a78bfa', 'legendary': '#fbbf24'}
CARD_RARITY_DISENCHANT = {'common': 1, 'rare': 3, 'epic': 8, 'legendary': 20}
CARD_DROP_RATES = {'common': 0.80, 'rare': 0.15, 'epic': 0.04, 'legendary': 0.01}

COUPON_DROP_TABLE = [
    {'discount': 10, 'weight': 50, 'desc': '会员开通立减10积分'},
    {'discount': 30, 'weight': 30, 'desc': '会员开通立减30积分'},
    {'discount': 50, 'weight': 15, 'desc': '会员开通立减50积分'},
    {'discount': 100, 'weight': 4, 'desc': '会员开通立减100积分'},
    {'discount': 288, 'weight': 1, 'desc': '会员开通立减288积分（免单）'}
]

POINTS_BONUS_TABLE = [
    {'amount': 0.5, 'weight': 50},
    {'amount': 1.0, 'weight': 30},
    {'amount': 2.0, 'weight': 15},
    {'amount': 5.0, 'weight': 4},
    {'amount': 10.0, 'weight': 1}
]

MEMBERSHIP_COUPON_EXPIRE_DAYS = 7
GCOIN_EXCHANGE_RATE = 100.0

GCOIN_EARN_TABLE = {
    'daily_first_win': 20,
    'achievement_unlock': 30,
    'level_up': 50,
    'weekly_login': 100,
    'checkin_streak_7': 80,
}

GCOIN_SPEND_TABLE = {
    'card_draw_single': 100,
    'card_draw_ten': 900,
    'ladder_entry': 50,
    'guild_donate': 200,
}


def get_membership_data(users, username):
    if username not in users:
        return None
    user_data = users[username]
    if 'membership' not in user_data:
        user_data['membership'] = {'is_member': False, 'tier': 'none', 'activated_at': 0, 'expires_at': 0, 'lifetime': False, 'auto_renew': False, 'previous_tier': 'none', 'renew_count': 0}
    if 'tier' not in user_data['membership']:
        user_data['membership']['tier'] = 'normal' if user_data['membership'].get('is_member', False) else 'none'
    if 'lifetime' not in user_data['membership']:
        user_data['membership']['lifetime'] = False
    if 'auto_renew' not in user_data['membership']:
        user_data['membership']['auto_renew'] = False
    if 'previous_tier' not in user_data['membership']:
        user_data['membership']['previous_tier'] = 'none'
    if 'renew_count' not in user_data['membership']:
        user_data['membership']['renew_count'] = 0
    return user_data['membership']


def is_game_member(users, username):
    membership = get_membership_data(users, username)
    if not membership:
        return False
    if not membership.get('is_member', False):
        return False
    if membership.get('lifetime', False):
        return True
    expires_at = membership.get('expires_at', 0)
    if expires_at == 0:
        return True
    if expires_at > int(time.time() * 1000):
        return True
    membership['is_member'] = False
    membership['previous_tier'] = membership.get('tier', 'none')
    membership['tier'] = 'none'
    membership['expires_at'] = 0
    return False


def get_member_tier(users, username):
    if not is_game_member(users, username):
        return 'none'
    membership = get_membership_data(users, username)
    return membership.get('tier', 'normal')


def get_member_max_plays(users, username):
    tier = get_member_tier(users, username)
    return MEMBERSHIP_TIERS.get(tier, MEMBERSHIP_TIERS['none'])['max_plays']


def get_member_bonus_rate(users, username):
    tier = get_member_tier(users, username)
    return MEMBERSHIP_TIERS.get(tier, MEMBERSHIP_TIERS['none'])['bonus_rate']


def get_member_daily_task_bonus(users, username):
    tier = get_member_tier(users, username)
    return MEMBERSHIP_TIERS.get(tier, MEMBERSHIP_TIERS['none'])['daily_task_bonus']


def get_member_exclusive_games(users, username):
    tier = get_member_tier(users, username)
    return MEMBERSHIP_TIERS.get(tier, MEMBERSHIP_TIERS['none'])['exclusive_games']


def get_member_drop_multiplier(users, username):
    tier = get_member_tier(users, username)
    return MEMBERSHIP_TIERS.get(tier, MEMBERSHIP_TIERS['none']).get('drop_multiplier', 1.0)


def get_member_expire_info(users, username):
    membership = get_membership_data(users, username)
    if not membership or not membership.get('is_member', False):
        return {'is_member': False, 'expires_at': 0, 'days_left': 0, 'hours_left': 0, 'is_expiring': False, 'is_lifetime': False}
    if membership.get('lifetime', False):
        return {'is_member': True, 'expires_at': 0, 'days_left': 99999, 'hours_left': 999999, 'is_expiring': False, 'is_lifetime': True}
    expires_at = membership.get('expires_at', 0)
    now_ms = int(time.time() * 1000)
    remain_ms = max(0, expires_at - now_ms)
    days_left = remain_ms // (24 * 3600 * 1000)
    hours_left = (remain_ms % (24 * 3600 * 1000)) // (3600 * 1000)
    is_expiring = remain_ms > 0 and remain_ms < 3 * 24 * 3600 * 1000
    return {
        'is_member': True,
        'expires_at': expires_at,
        'days_left': days_left,
        'hours_left': hours_left,
        'is_expiring': is_expiring,
        'is_lifetime': False
    }


def check_supreme_requirements(users, username):
    if username not in users:
        return False, 0, 0.0
    user_data = users[username]
    game_stats = user_data.get('game_stats', {})
    total_plays = game_stats.get('total_plays', 0)
    total_wins = game_stats.get('total_wins', 0)
    win_rate = round(total_wins / max(1, total_plays) * 100, 1) if total_plays > 0 else 0.0
    req = MEMBERSHIP_TIERS['supreme']['requirements']
    meets = total_plays >= req['min_total_plays'] and win_rate > req['min_win_rate']
    return meets, total_plays, win_rate


def _is_lifetime_tier(tier):
    return tier.endswith('_lifetime')


def _get_base_tier(tier):
    if _is_lifetime_tier(tier):
        return tier.replace('_lifetime', '')
    return tier


def activate_game_membership(users, save_users_func, username, tier='normal', coupon_id=None):
    if username not in users:
        return False, '用户不存在', 0
    if tier not in MEMBERSHIP_TIERS or tier == 'none':
        return False, '无效的会员等级', 0
    tier_info = MEMBERSHIP_TIERS[tier]
    price = tier_info['price']
    user_data = users[username]
    total_plays = 0
    win_rate = 0.0
    if _get_base_tier(tier) == 'supreme':
        meets, total_plays, win_rate = check_supreme_requirements(users, username)
        if not meets:
            req = MEMBERSHIP_TIERS['supreme']['requirements']
            return False, f'至尊会员需要总局数≥{req["min_total_plays"]}且胜率>{req["min_win_rate"]}%，当前{total_plays}局，胜率{win_rate}%', 0
    current_tier = get_member_tier(users, username)
    if current_tier != 'none':
        return False, f'您已是{MEMBERSHIP_TIERS[current_tier]["name"]}，请使用升级功能', 0
    final_price = price
    coupon_discount = 0
    if coupon_id:
        coupon = _find_membership_coupon(users, username, coupon_id)
        if coupon and coupon.get('discount', 0) <= price:
            coupon_discount = coupon['discount']
            final_price = round(price - coupon_discount, 2)
    if user_data.get('totalPoints', 0) < final_price:
        return False, f'积分不足，需要 {final_price} 积分', 0
    user_data['totalPoints'] = round(user_data['totalPoints'] - final_price, 2)
    if 'membership' not in user_data:
        user_data['membership'] = {}
    now_ms = int(time.time() * 1000)
    duration_days = tier_info.get('duration_days', 30)
    is_lifetime = duration_days == 0
    user_data['membership']['is_member'] = True
    user_data['membership']['tier'] = tier
    user_data['membership']['activated_at'] = now_ms
    user_data['membership']['expires_at'] = 0 if is_lifetime else (now_ms + duration_days * 24 * 3600 * 1000)
    user_data['membership']['lifetime'] = is_lifetime
    user_data['membership']['auto_renew'] = tier_info.get('auto_renew', False) and not is_lifetime
    user_data['membership']['previous_tier'] = 'none'
    user_data['membership']['renew_count'] = 0
    if _get_base_tier(tier) == 'supreme':
        user_data['membership']['supreme_snapshot'] = {'total_plays': total_plays, 'win_rate': win_rate, 'purchased_at': now_ms}
    if coupon_id:
        _mark_membership_coupon_used(users, username, coupon_id)
    save_users_func()
    msg = f'{tier_info["name"]}开通成功！每日游戏次数提升至{tier_info["max_plays"]}次，获胜G币+{int(tier_info["bonus_rate"]*100)}%'
    if not is_lifetime:
        msg += f'，有效期{duration_days}天'
    if coupon_discount > 0:
        msg += f'（优惠券抵扣{coupon_discount}积分）'
    return True, msg, final_price


def upgrade_membership(users, save_users_func, username, new_tier, coupon_id=None):
    if username not in users:
        return False, '用户不存在', 0
    if new_tier not in MEMBERSHIP_TIERS or new_tier == 'none':
        return False, '无效的会员等级', 0
    current_tier = get_member_tier(users, username)
    if current_tier == 'none':
        return False, '您还不是会员，请先开通', 0
    tier_order = {'none': 0, 'normal': 1, 'gold': 2, 'diamond': 3, 'supreme': 4,
                  'normal_lifetime': 1, 'gold_lifetime': 2, 'diamond_lifetime': 3}
    current_base = _get_base_tier(current_tier)
    new_base = _get_base_tier(new_tier)
    if tier_order.get(new_base, 0) <= tier_order.get(current_base, 0):
        return False, '只能升级到更高等级', 0
    total_plays = 0
    win_rate = 0.0
    if new_base == 'supreme':
        meets, total_plays, win_rate = check_supreme_requirements(users, username)
        if not meets:
            req = MEMBERSHIP_TIERS['supreme']['requirements']
            return False, f'至尊会员需要总局数≥{req["min_total_plays"]}且胜率>{req["min_win_rate"]}%，当前{total_plays}局，胜率{win_rate}%', 0
    current_price = MEMBERSHIP_TIERS.get(current_tier, MEMBERSHIP_TIERS['none'])['price']
    new_price = MEMBERSHIP_TIERS[new_tier]['price']
    upgrade_price = round(new_price - current_price, 2)
    if upgrade_price <= 0:
        return False, '升级价格无效', 0
    user_data = users[username]
    coupon_discount = 0
    if coupon_id:
        coupon = _find_membership_coupon(users, username, coupon_id)
        if coupon and coupon.get('discount', 0) <= upgrade_price:
            coupon_discount = coupon['discount']
            upgrade_price = round(upgrade_price - coupon_discount, 2)
    if user_data.get('totalPoints', 0) < upgrade_price:
        return False, f'积分不足，升级需要 {upgrade_price} 积分', 0
    user_data['totalPoints'] = round(user_data['totalPoints'] - upgrade_price, 2)
    now_ms = int(time.time() * 1000)
    tier_info = MEMBERSHIP_TIERS[new_tier]
    duration_days = tier_info.get('duration_days', 30)
    is_lifetime = duration_days == 0
    user_data['membership']['tier'] = new_tier
    user_data['membership']['is_member'] = True
    user_data['membership']['activated_at'] = now_ms
    user_data['membership']['expires_at'] = 0 if is_lifetime else (now_ms + duration_days * 24 * 3600 * 1000)
    user_data['membership']['lifetime'] = is_lifetime
    user_data['membership']['auto_renew'] = tier_info.get('auto_renew', False) and not is_lifetime
    if new_base == 'supreme':
        user_data['membership']['supreme_snapshot'] = {'total_plays': total_plays, 'win_rate': win_rate, 'purchased_at': now_ms}
    if coupon_id:
        _mark_membership_coupon_used(users, username, coupon_id)
    save_users_func()
    msg = f'升级成功！当前为{tier_info["name"]}，每日{tier_info["max_plays"]}次，+{int(tier_info["bonus_rate"]*100)}%'
    if not is_lifetime:
        msg += f'，有效期{duration_days}天'
    if coupon_discount > 0:
        msg += f'（优惠券抵扣{coupon_discount}积分）'
    return True, msg, upgrade_price


def renew_membership(users, save_users_func, username):
    if username not in users:
        return False, '用户不存在', 0
    membership = get_membership_data(users, username)
    if not membership or not membership.get('is_member', False):
        return False, '您还不是会员，请先开通', 0
    if membership.get('lifetime', False):
        return False, '永久会员无需续费', 0
    current_tier = membership.get('tier', 'none')
    if current_tier == 'none':
        return False, '会员等级异常', 0
    tier_info = MEMBERSHIP_TIERS.get(current_tier)
    if not tier_info:
        return False, '会员等级异常', 0
    renew_count = membership.get('renew_count', 0)
    discount = 1.0
    if renew_count >= 3:
        discount = 0.8
    elif renew_count >= 2:
        discount = 0.85
    elif renew_count >= 1:
        discount = 0.9
    base_price = tier_info['price']
    renew_price = round(base_price * discount, 2)
    user_data = users[username]
    if user_data.get('totalPoints', 0) < renew_price:
        return False, f'积分不足，续费需要 {renew_price} 积分', 0
    user_data['totalPoints'] = round(user_data['totalPoints'] - renew_price, 2)
    now_ms = int(time.time() * 1000)
    duration_days = tier_info.get('duration_days', 30)
    current_expires = membership.get('expires_at', 0)
    base_time = max(now_ms, current_expires)
    membership['expires_at'] = base_time + duration_days * 24 * 3600 * 1000
    membership['renew_count'] = renew_count + 1
    membership['last_renew_at'] = now_ms
    save_users_func()
    return True, f'续费成功！有效期延长{duration_days}天（{int(discount*100)}折优惠）', renew_price


def admin_revoke_membership(users, save_users_func, username, refund=True):
    if username not in users:
        return False, '用户不存在', 0, None
    user_data = users[username]
    if 'membership' not in user_data:
        return False, '该用户不是会员', 0, None
    membership = user_data['membership']
    if not membership.get('is_member', False):
        return False, '该用户不是会员', 0, None
    old_tier = membership.get('tier', 'none')
    tier_info = MEMBERSHIP_TIERS.get(old_tier)
    if not tier_info:
        return False, '会员等级数据异常', 0, None
    refund_amount = 0
    refund_detail = ''
    if refund:
        full_price = tier_info.get('price', 0)
        is_lifetime = tier_info.get('duration_days', 30) == 0
        if is_lifetime:
            refund_amount = full_price
            refund_detail = f'永久会员全额退款 {full_price} 积分'
        else:
            duration_days = tier_info.get('duration_days', 30)
            duration_ms = duration_days * 24 * 3600 * 1000
            expires_at = membership.get('expires_at', 0)
            now_ms = int(time.time() * 1000)
            if expires_at > 0 and duration_ms > 0:
                remain_ms = max(0, expires_at - now_ms)
                remain_ratio = remain_ms / duration_ms
                remain_ratio = min(1.0, max(0.0, remain_ratio))
                refund_amount = round(full_price * remain_ratio, 2)
                remain_days = remain_ms / (24 * 3600 * 1000)
                refund_detail = f'月卡剩余 {remain_days:.1f} 天，按比例退款 {refund_amount} / {full_price} 积分'
            else:
                refund_amount = full_price
                refund_detail = f'月卡全额退款 {full_price} 积分'
    snapshot = {
        'username': username,
        'old_tier': old_tier,
        'old_tier_name': tier_info.get('name', old_tier),
        'activated_at': membership.get('activated_at', 0),
        'expires_at': membership.get('expires_at', 0),
        'lifetime': membership.get('lifetime', False),
        'refund_amount': refund_amount,
        'refund_detail': refund_detail,
        'revoked_at': int(time.time() * 1000)
    }
    membership['is_member'] = False
    membership['previous_tier'] = old_tier
    membership['tier'] = 'none'
    membership['expires_at'] = 0
    membership['lifetime'] = False
    membership['auto_renew'] = False
    membership['revoked_at'] = int(time.time() * 1000)
    membership['revoke_snapshot'] = snapshot
    if 'revoke_history' not in user_data:
        user_data['revoke_history'] = []
    user_data['revoke_history'].insert(0, snapshot)
    if len(user_data['revoke_history']) > 20:
        user_data['revoke_history'] = user_data['revoke_history'][:20]
    save_users_func()
    return True, f'已移除会员（原等级：{tier_info.get("name", old_tier)}）', refund_amount, snapshot


def admin_restore_membership(users, save_users_func, username):
    if username not in users:
        return False, '用户不存在'
    user_data = users[username]
    membership = user_data.get('membership', {})
    snapshot = membership.get('revoke_snapshot')
    if not snapshot:
        return False, '没有可恢复的会员记录'
    old_tier = snapshot.get('old_tier', 'none')
    if old_tier == 'none' or old_tier not in MEMBERSHIP_TIERS:
        return False, '会员等级数据异常'
    tier_info = MEMBERSHIP_TIERS[old_tier]
    is_lifetime = tier_info.get('duration_days', 30) == 0
    now_ms = int(time.time() * 1000)
    membership['is_member'] = True
    membership['tier'] = old_tier
    membership['activated_at'] = now_ms
    if is_lifetime:
        membership['expires_at'] = 0
        membership['lifetime'] = True
    else:
        expires_at = snapshot.get('expires_at', 0)
        if expires_at > now_ms:
            membership['expires_at'] = expires_at
        else:
            membership['expires_at'] = now_ms + tier_info.get('duration_days', 30) * 24 * 3600 * 1000
        membership['lifetime'] = False
    membership['auto_renew'] = tier_info.get('auto_renew', False)
    membership['restored_at'] = now_ms
    save_users_func()
    return True, f'已恢复会员：{tier_info.get("name", old_tier)}'


def migrate_game_membership_data(users, save_users_func):
    modified = False
    for username, user_data in users.items():
        if 'membership' not in user_data:
            user_data['membership'] = {'is_member': False, 'tier': 'none', 'activated_at': 0, 'expires_at': 0, 'lifetime': False, 'auto_renew': False, 'previous_tier': 'none', 'renew_count': 0}
            modified = True
        else:
            membership = user_data['membership']
            if 'lifetime' not in membership:
                membership['lifetime'] = False
                modified = True
            if 'activated_at' not in membership:
                membership['activated_at'] = 0
                modified = True
            if 'expires_at' not in membership:
                membership['expires_at'] = 0
                modified = True
            if 'is_member' not in membership:
                membership['is_member'] = False
                modified = True
            if 'tier' not in membership:
                membership['tier'] = 'normal' if membership.get('is_member', False) else 'none'
                modified = True
            if 'auto_renew' not in membership:
                membership['auto_renew'] = False
                modified = True
            if 'previous_tier' not in membership:
                membership['previous_tier'] = 'none'
                modified = True
            if 'renew_count' not in membership:
                membership['renew_count'] = 0
                modified = True
    if modified:
        save_users_func()
    return modified


def _find_membership_coupon(users, username, coupon_id):
    user_data = users.get(username, {})
    coupons = user_data.get('membership_coupons', {})
    coupon = coupons.get(coupon_id)
    if not coupon:
        return None
    if coupon.get('used', False):
        return None
    if coupon.get('expire_at', 0) < int(time.time() * 1000):
        return None
    return coupon


def _mark_membership_coupon_used(users, username, coupon_id):
    user_data = users.get(username, {})
    coupons = user_data.get('membership_coupons', {})
    if coupon_id in coupons:
        coupons[coupon_id]['used'] = True
        coupons[coupon_id]['used_at'] = int(time.time() * 1000)


def get_user_membership_coupons(users, username):
    user_data = users.get(username, {})
    coupons = user_data.get('membership_coupons', {})
    now_ms = int(time.time() * 1000)
    result = []
    for cid, c in coupons.items():
        if c.get('used', False):
            continue
        if c.get('expire_at', 0) < now_ms:
            continue
        result.append({
            'id': cid,
            'discount': c.get('discount', 0),
            'description': c.get('description', ''),
            'expire_at': c.get('expire_at', 0),
            'created_at': c.get('created_at', 0)
        })
    result.sort(key=lambda x: -x['discount'])
    return result


def get_best_membership_coupon(users, username, tier_price):
    coupons = get_user_membership_coupons(users, username)
    best = None
    for c in coupons:
        if c['discount'] > tier_price:
            continue
        if best is None or c['discount'] > best['discount']:
            best = c
    return best


def get_gcoin_data(users, username):
    if username not in users:
        return None
    user_data = users[username]
    if 'gcoins' not in user_data:
        user_data['gcoins'] = {'balance': 0, 'total_earned': 0, 'total_spent': 0}
    return user_data['gcoins']


def add_gcoins(users, username, amount, reason=''):
    if username not in users:
        return False
    user_data = users[username]
    if 'gcoins' not in user_data:
        user_data['gcoins'] = {'balance': 0, 'total_earned': 0, 'total_spent': 0}
    if amount > 0:
        user_data['gcoins']['balance'] = user_data['gcoins'].get('balance', 0) + amount
        user_data['gcoins']['total_earned'] = user_data['gcoins'].get('total_earned', 0) + amount
    else:
        user_data['gcoins']['balance'] = max(0, user_data['gcoins'].get('balance', 0) + amount)
        user_data['gcoins']['total_spent'] = user_data['gcoins'].get('total_spent', 0) + abs(amount)
    return True


def spend_gcoins(users, username, amount, reason=''):
    if username not in users:
        return False, '用户不存在'
    user_data = users[username]
    if 'gcoins' not in user_data:
        return False, 'G币余额不足'
    if user_data['gcoins'].get('balance', 0) < amount:
        return False, f'G币余额不足，需要 {amount} G币'
    user_data['gcoins']['balance'] = user_data['gcoins'].get('balance', 0) - amount
    user_data['gcoins']['total_spent'] = user_data['gcoins'].get('total_spent', 0) + amount
    return True, '扣除成功'


def exchange_points_to_gcoins(users, save_users_func, username, points_amount):
    if username not in users:
        return False, '用户不存在', 0
    user_data = users[username]
    if user_data.get('totalPoints', 0) < points_amount:
        return False, f'积分不足，需要 {points_amount} 积分', 0
    gcoin_amount = int(points_amount * GCOIN_EXCHANGE_RATE)
    user_data['totalPoints'] = round(user_data['totalPoints'] - points_amount, 2)
    add_gcoins(users, username, gcoin_amount, 'points_exchange')
    save_users_func()
    return True, f'兑换成功！{points_amount} 积分 = {gcoin_amount} G币', gcoin_amount


def exchange_gcoins_to_points(users, save_users_func, username, gcoin_amount):
    if username not in users:
        return False, '用户不存在', 0
    user_data = users[username]
    if 'gcoins' not in user_data or user_data['gcoins'].get('balance', 0) < gcoin_amount:
        return False, 'G币余额不足', 0
    points_amount = round(gcoin_amount / GCOIN_EXCHANGE_RATE, 2)
    user_data['gcoins']['balance'] = user_data['gcoins'].get('balance', 0) - gcoin_amount
    user_data['gcoins']['total_spent'] = user_data['gcoins'].get('total_spent', 0) + gcoin_amount
    user_data['totalPoints'] = round(user_data.get('totalPoints', 0) + points_amount, 2)
    save_users_func()
    return True, f'兑换成功！{gcoin_amount} G币 = {points_amount} 积分', points_amount


def get_market_listings(users):
    all_listings = []
    for username, user_data in users.items():
        listings = user_data.get('market_listings', {})
        for listing_id, listing in listings.items():
            if listing.get('status') != 'active':
                continue
            if listing.get('expires_at', 0) > 0 and listing['expires_at'] < int(time.time() * 1000):
                continue
            all_listings.append({
                'id': listing_id,
                'seller': username,
                'game_id': listing.get('game_id', ''),
                'card_id': listing.get('card_id', ''),
                'card_name': listing.get('card_name', ''),
                'card_emoji': listing.get('card_emoji', ''),
                'rarity': listing.get('rarity', 'common'),
                'rarity_name': CARD_RARITY_NAMES.get(listing.get('rarity', 'common'), ''),
                'rarity_color': CARD_RARITY_COLORS.get(listing.get('rarity', 'common'), '#fff'),
                'quantity': listing.get('quantity', 1),
                'price_gcoins': listing.get('price_gcoins', 0),
                'created_at': listing.get('created_at', 0),
                'expires_at': listing.get('expires_at', 0)
            })
    all_listings.sort(key=lambda x: -x.get('created_at', 0))
    return all_listings


def get_user_market_listings(users, username):
    if username not in users:
        return []
    user_data = users[username]
    listings = user_data.get('market_listings', {})
    result = []
    for listing_id, listing in listings.items():
        if listing.get('status') != 'active':
            continue
        result.append({
            'id': listing_id,
            'game_id': listing.get('game_id', ''),
            'card_id': listing.get('card_id', ''),
            'card_name': listing.get('card_name', ''),
            'card_emoji': listing.get('card_emoji', ''),
            'rarity': listing.get('rarity', 'common'),
            'rarity_name': CARD_RARITY_NAMES.get(listing.get('rarity', 'common'), ''),
            'rarity_color': CARD_RARITY_COLORS.get(listing.get('rarity', 'common'), '#fff'),
            'quantity': listing.get('quantity', 1),
            'price_gcoins': listing.get('price_gcoins', 0),
            'created_at': listing.get('created_at', 0),
            'expires_at': listing.get('expires_at', 0)
        })
    result.sort(key=lambda x: -x.get('created_at', 0))
    return result


def create_market_listing(users, save_users_func, username, game_id, card_id, quantity, price_gcoins):
    if username not in users:
        return False, '用户不存在', None
    if quantity < 1 or quantity > 99:
        return False, '数量必须在1-99之间', None
    if price_gcoins < 1 or price_gcoins > 1000000:
        return False, '价格必须在1-1000000 G币之间', None
    user_data = users[username]
    if 'card_collection' not in user_data or game_id not in user_data['card_collection']:
        return False, '未拥有该卡牌', None
    owned = user_data['card_collection'][game_id]
    if owned.get(card_id, 0) < quantity + 1:
        return False, f'至少需保留1张，当前拥有 {owned.get(card_id, 0)} 张', None
    card_info = None
    if game_id in CARD_COLLECTIONS:
        for card in CARD_COLLECTIONS[game_id]['cards']:
            if card['id'] == card_id:
                card_info = card
                break
    if not card_info:
        return False, '卡牌不存在', None
    if 'market_listings' not in user_data:
        user_data['market_listings'] = {}
    listing_id = f"lst_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    owned[card_id] -= quantity
    user_data['market_listings'][listing_id] = {
        'id': listing_id,
        'game_id': game_id,
        'card_id': card_id,
        'card_name': card_info['name'],
        'card_emoji': card_info['emoji'],
        'rarity': card_info['rarity'],
        'quantity': quantity,
        'price_gcoins': price_gcoins,
        'status': 'active',
        'created_at': int(time.time() * 1000),
        'expires_at': int(time.time() * 1000) + 7 * 24 * 3600 * 1000
    }
    save_users_func()
    return True, f'上架成功！{card_info["emoji"]} {card_info["name"]} x{quantity}，单价 {price_gcoins} G币', listing_id


def cancel_market_listing(users, save_users_func, username, listing_id):
    if username not in users:
        return False, '用户不存在'
    user_data = users[username]
    if 'market_listings' not in user_data or listing_id not in user_data['market_listings']:
        return False, '挂单不存在'
    listing = user_data['market_listings'][listing_id]
    if listing.get('status') != 'active':
        return False, '挂单状态异常'
    game_id = listing.get('game_id', '')
    card_id = listing.get('card_id', '')
    quantity = listing.get('quantity', 1)
    if 'card_collection' not in user_data:
        user_data['card_collection'] = {}
    if game_id not in user_data['card_collection']:
        user_data['card_collection'][game_id] = {}
    user_data['card_collection'][game_id][card_id] = user_data['card_collection'][game_id].get(card_id, 0) + quantity
    listing['status'] = 'cancelled'
    listing['cancelled_at'] = int(time.time() * 1000)
    save_users_func()
    return True, f'已取消挂单，{quantity} 张卡牌已返还'


def buy_market_listing(users, save_users_func, buyer, listing_id):
    if buyer not in users:
        return False, '买家不存在', None
    target_seller = None
    target_listing = None
    for username, user_data in users.items():
        if 'market_listings' in user_data and listing_id in user_data['market_listings']:
            if user_data['market_listings'][listing_id].get('status') == 'active':
                target_seller = username
                target_listing = user_data['market_listings'][listing_id]
                break
    if not target_listing:
        return False, '挂单不存在或已下架', None
    if target_seller == buyer:
        return False, '不能购买自己的挂单', None
    price = target_listing.get('price_gcoins', 0)
    quantity = target_listing.get('quantity', 1)
    total_price = price * quantity
    buyer_data = users[buyer]
    if 'gcoins' not in buyer_data or buyer_data['gcoins'].get('balance', 0) < total_price:
        return False, f'G币余额不足，需要 {total_price} G币', None
    buyer_data['gcoins']['balance'] = buyer_data['gcoins'].get('balance', 0) - total_price
    buyer_data['gcoins']['total_spent'] = buyer_data['gcoins'].get('total_spent', 0) + total_price
    system_fee = int(total_price * 0.05)
    seller_receive = total_price - system_fee
    seller_data = users[target_seller]
    if 'gcoins' not in seller_data:
        seller_data['gcoins'] = {'balance': 0, 'total_earned': 0, 'total_spent': 0}
    seller_data['gcoins']['balance'] = seller_data['gcoins'].get('balance', 0) + seller_receive
    seller_data['gcoins']['total_earned'] = seller_data['gcoins'].get('total_earned', 0) + seller_receive
    game_id = target_listing.get('game_id', '')
    card_id = target_listing.get('card_id', '')
    if 'card_collection' not in buyer_data:
        buyer_data['card_collection'] = {}
    if game_id not in buyer_data['card_collection']:
        buyer_data['card_collection'][game_id] = {}
    buyer_data['card_collection'][game_id][card_id] = buyer_data['card_collection'][game_id].get(card_id, 0) + quantity
    target_listing['status'] = 'sold'
    target_listing['sold_at'] = int(time.time() * 1000)
    target_listing['buyer'] = buyer
    target_listing['seller_receive'] = seller_receive
    target_listing['system_fee'] = system_fee
    buyer_stats = buyer_data.get('game_stats', {})
    if 'market_trades' not in buyer_stats:
        buyer_stats['market_trades'] = 0
    buyer_stats['market_trades'] += 1
    seller_stats = seller_data.get('game_stats', {})
    if 'market_trades' not in seller_stats:
        seller_stats['market_trades'] = 0
    seller_stats['market_trades'] += 1
    save_users_func()
    detail = {
        'total_price': total_price,
        'seller_receive': seller_receive,
        'system_fee': system_fee,
        'card_name': target_listing.get('card_name', ''),
        'card_emoji': target_listing.get('card_emoji', ''),
        'quantity': quantity,
        'seller': target_seller
    }
    return True, f'购买成功！{target_listing.get("card_emoji", "")} {target_listing.get("card_name", "")} x{quantity}，花费 {total_price} G币', detail


def get_auctions(users):
    result = []
    for username, user_data in users.items():
        auctions = user_data.get('auctions', {})
        for auction_id, auction in auctions.items():
            if auction.get('status') != 'active':
                continue
            if auction.get('end_at', 0) > 0 and auction['end_at'] < int(time.time() * 1000):
                continue
            result.append({
                'id': auction_id,
                'seller': username,
                'game_id': auction.get('game_id', ''),
                'card_id': auction.get('card_id', ''),
                'card_name': auction.get('card_name', ''),
                'card_emoji': auction.get('card_emoji', ''),
                'rarity': auction.get('rarity', 'common'),
                'rarity_name': CARD_RARITY_NAMES.get(auction.get('rarity', 'common'), ''),
                'rarity_color': CARD_RARITY_COLORS.get(auction.get('rarity', 'common'), '#fff'),
                'start_price': auction.get('start_price', 0),
                'current_bid': auction.get('current_bid', 0),
                'current_bidder': auction.get('current_bidder', ''),
                'bid_count': len(auction.get('bids', [])),
                'start_at': auction.get('start_at', 0),
                'end_at': auction.get('end_at', 0),
                'created_at': auction.get('created_at', 0),
                'is_server_generated': False
            })
    result.sort(key=lambda x: x.get('end_at', 0))
    return result


def create_auction(users, save_users_func, username, game_id, card_id, start_price, duration_hours=24):
    if username not in users:
        return False, '用户不存在', None
    if start_price < 10 or start_price > 1000000:
        return False, '起拍价必须在10-1000000 G币之间', None
    if duration_hours < 1 or duration_hours > 72:
        return False, '拍卖时长必须在1-72小时之间', None
    user_data = users[username]
    if 'card_collection' not in user_data or game_id not in user_data['card_collection']:
        return False, '未拥有该卡牌', None
    owned = user_data['card_collection'][game_id]
    if owned.get(card_id, 0) < 2:
        return False, '至少需保留1张，当前拥有不足2张', None
    card_info = None
    if game_id in CARD_COLLECTIONS:
        for card in CARD_COLLECTIONS[game_id]['cards']:
            if card['id'] == card_id:
                card_info = card
                break
    if not card_info:
        return False, '卡牌不存在', None
    if 'auctions' not in user_data:
        user_data['auctions'] = {}
    auction_id = f"auc_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    owned[card_id] -= 1
    now_ms = int(time.time() * 1000)
    user_data['auctions'][auction_id] = {
        'id': auction_id,
        'game_id': game_id,
        'card_id': card_id,
        'card_name': card_info['name'],
        'card_emoji': card_info['emoji'],
        'rarity': card_info['rarity'],
        'start_price': start_price,
        'current_bid': start_price,
        'current_bidder': '',
        'bids': [],
        'status': 'active',
        'start_at': now_ms,
        'end_at': now_ms + duration_hours * 3600 * 1000,
        'created_at': now_ms
    }
    save_users_func()
    return True, f'拍卖已创建！{card_info["emoji"]} {card_info["name"]}，起拍价 {start_price} G币，时长 {duration_hours} 小时', auction_id


def place_bid(users, save_users_func, bidder, auction_id, bid_amount):
    if bidder not in users:
        return False, '用户不存在'
    target_seller = None
    target_auction = None
    for username, user_data in users.items():
        if 'auctions' in user_data and auction_id in user_data['auctions']:
            if user_data['auctions'][auction_id].get('status') == 'active':
                target_seller = username
                target_auction = user_data['auctions'][auction_id]
                break
    if not target_auction:
        return False, '拍卖不存在或已结束'
    if target_seller == bidder:
        return False, '不能竞拍自己的拍卖'
    now_ms = int(time.time() * 1000)
    if target_auction.get('end_at', 0) < now_ms:
        return False, '拍卖已结束'
    current_bid = target_auction.get('current_bid', 0)
    min_bid = current_bid + 10
    if bid_amount < min_bid:
        return False, f'出价必须高于当前价 {current_bid} G币，最低 {min_bid} G币'
    bidder_data = users[bidder]
    if 'gcoins' not in bidder_data or bidder_data['gcoins'].get('balance', 0) < bid_amount:
        return False, f'G币余额不足，需要 {bid_amount} G币'
    prev_bidder = target_auction.get('current_bidder', '')
    prev_bid = target_auction.get('current_bid', 0)
    if prev_bidder and prev_bidder in users:
        prev_data = users[prev_bidder]
        if 'gcoins' not in prev_data:
            prev_data['gcoins'] = {'balance': 0, 'total_earned': 0, 'total_spent': 0}
        prev_data['gcoins']['balance'] = prev_data['gcoins'].get('balance', 0) + prev_bid
        prev_data['gcoins']['total_spent'] = max(0, prev_data['gcoins'].get('total_spent', 0) - prev_bid)
    bidder_data['gcoins']['balance'] = bidder_data['gcoins'].get('balance', 0) - bid_amount
    bidder_data['gcoins']['total_spent'] = bidder_data['gcoins'].get('total_spent', 0) + bid_amount
    target_auction['current_bid'] = bid_amount
    target_auction['current_bidder'] = bidder
    if 'bids' not in target_auction:
        target_auction['bids'] = []
    target_auction['bids'].append({
        'bidder': bidder,
        'amount': bid_amount,
        'timestamp': now_ms
    })
    save_users_func()
    return True, f'出价成功！当前最高价 {bid_amount} G币'


def settle_auction(users, save_users_func, auction_id):
    target_seller = None
    target_auction = None
    for username, user_data in users.items():
        if 'auctions' in user_data and auction_id in user_data['auctions']:
            target_seller = username
            target_auction = user_data['auctions'][auction_id]
            break
    if not target_auction:
        return False, '拍卖不存在', 0
    if target_auction.get('status') != 'active':
        return False, '拍卖状态异常', 0
    now_ms = int(time.time() * 1000)
    if target_auction.get('end_at', 0) > now_ms:
        return False, '拍卖尚未结束', 0
    winner = target_auction.get('current_bidder', '')
    final_price = target_auction.get('current_bid', 0)
    seller_data = users[target_seller]
    if not winner:
        game_id = target_auction.get('game_id', '')
        card_id = target_auction.get('card_id', '')
        if 'card_collection' not in seller_data:
            seller_data['card_collection'] = {}
        if game_id not in seller_data['card_collection']:
            seller_data['card_collection'][game_id] = {}
        seller_data['card_collection'][game_id][card_id] = seller_data['card_collection'][game_id].get(card_id, 0) + 1
        target_auction['status'] = 'unsold'
        target_auction['settled_at'] = now_ms
        save_users_func()
        return True, '拍卖无人出价，卡牌已返还', 0
    if winner not in users:
        target_auction['status'] = 'failed'
        target_auction['settled_at'] = now_ms
        save_users_func()
        return False, '买家不存在', 0
    system_fee = int(final_price * 0.05)
    seller_receive = final_price - system_fee
    if 'gcoins' not in seller_data:
        seller_data['gcoins'] = {'balance': 0, 'total_earned': 0, 'total_spent': 0}
    seller_data['gcoins']['balance'] = seller_data['gcoins'].get('balance', 0) + seller_receive
    seller_data['gcoins']['total_earned'] = seller_data['gcoins'].get('total_earned', 0) + seller_receive
    winner_data = users[winner]
    game_id = target_auction.get('game_id', '')
    card_id = target_auction.get('card_id', '')
    if 'card_collection' not in winner_data:
        winner_data['card_collection'] = {}
    if game_id not in winner_data['card_collection']:
        winner_data['card_collection'][game_id] = {}
    winner_data['card_collection'][game_id][card_id] = winner_data['card_collection'][game_id].get(card_id, 0) + 1
    winner_stats = winner_data.get('game_stats', {})
    if 'auction_wins' not in winner_stats:
        winner_stats['auction_wins'] = 0
    winner_stats['auction_wins'] += 1
    target_auction['status'] = 'sold'
    target_auction['settled_at'] = now_ms
    target_auction['winner'] = winner
    target_auction['final_price'] = final_price
    target_auction['seller_receive'] = seller_receive
    target_auction['system_fee'] = system_fee
    save_users_func()
    return True, f'拍卖成交！{winner} 以 {final_price} G币赢得 {target_auction.get("card_name", "")}', final_price


def cancel_auction(users, save_users_func, username, auction_id):
    if username not in users:
        return False, '用户不存在'
    user_data = users[username]
    if 'auctions' not in user_data or auction_id not in user_data['auctions']:
        return False, '拍卖不存在'
    auction = user_data['auctions'][auction_id]
    if auction.get('status') != 'active':
        return False, '拍卖状态异常'
    if auction.get('current_bidder'):
        return False, '已有用户出价，无法取消'
    game_id = auction.get('game_id', '')
    card_id = auction.get('card_id', '')
    if 'card_collection' not in user_data:
        user_data['card_collection'] = {}
    if game_id not in user_data['card_collection']:
        user_data['card_collection'][game_id] = {}
    user_data['card_collection'][game_id][card_id] = user_data['card_collection'][game_id].get(card_id, 0) + 1
    auction['status'] = 'cancelled'
    auction['cancelled_at'] = int(time.time() * 1000)
    save_users_func()
    return True, '拍卖已取消，卡牌已返还'


def get_all_legendary_cards():
    result = []
    for game_id, collection in CARD_COLLECTIONS.items():
        for card in collection['cards']:
            if card.get('rarity') == 'legendary':
                result.append({
                    'game_id': game_id,
                    'game_name': collection['name'],
                    'game_icon': collection['icon'],
                    'card_id': card['id'],
                    'card_name': card['name'],
                    'card_emoji': card['emoji'],
                    'rarity': card['rarity']
                })
    return result


def server_create_auction(game_id, card_id, start_price, duration_hours=24, analytics_cache_ref=None, save_analytics_func=None):
    legendary_cards = get_all_legendary_cards()
    target_card = None
    for card in legendary_cards:
        if card['game_id'] == game_id and card['card_id'] == card_id:
            target_card = card
            break
    if not target_card:
        return False, '卡牌不存在或非传说卡', None
    if analytics_cache_ref is None:
        return False, '内部错误：缺少缓存引用', None
    if 'server_auctions' not in analytics_cache_ref:
        analytics_cache_ref['server_auctions'] = {}
    server_auctions = analytics_cache_ref['server_auctions']
    auction_id = f"srv_auc_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    now_ms = int(time.time() * 1000)
    server_auctions[auction_id] = {
        'id': auction_id,
        'game_id': game_id,
        'card_id': card_id,
        'card_name': target_card['card_name'],
        'card_emoji': target_card['card_emoji'],
        'rarity': target_card['rarity'],
        'start_price': start_price,
        'current_bid': start_price,
        'current_bidder': '',
        'bids': [],
        'status': 'active',
        'is_server_generated': True,
        'start_at': now_ms,
        'end_at': now_ms + duration_hours * 3600 * 1000,
        'created_at': now_ms
    }
    if save_analytics_func:
        save_analytics_func()
    return True, f'服务器已创建传说卡拍卖：{target_card["card_emoji"]} {target_card["card_name"]}，起拍价 {start_price} G币', auction_id


def get_server_auctions(analytics_cache_ref):
    if not analytics_cache_ref or 'server_auctions' not in analytics_cache_ref:
        return []
    now_ms = int(time.time() * 1000)
    result = []
    for auc_id, auc in analytics_cache_ref['server_auctions'].items():
        if auc.get('status') != 'active':
            continue
        if auc.get('end_at', 0) < now_ms:
            continue
        result.append({
            'id': auc_id,
            'seller': '服务器',
            'game_id': auc.get('game_id', ''),
            'card_id': auc.get('card_id', ''),
            'card_name': auc.get('card_name', ''),
            'card_emoji': auc.get('card_emoji', ''),
            'rarity': auc.get('rarity', 'common'),
            'rarity_name': CARD_RARITY_NAMES.get(auc.get('rarity', 'common'), ''),
            'rarity_color': CARD_RARITY_COLORS.get(auc.get('rarity', 'common'), '#fff'),
            'start_price': auc.get('start_price', 0),
            'current_bid': auc.get('current_bid', 0),
            'current_bidder': auc.get('current_bidder', ''),
            'bid_count': len(auc.get('bids', [])),
            'is_server_generated': True,
            'start_at': auc.get('start_at', 0),
            'end_at': auc.get('end_at', 0),
            'created_at': auc.get('created_at', 0)
        })
    result.sort(key=lambda x: x.get('end_at', 0))
    return result


def get_all_auctions_combined(users, analytics_cache_ref):
    user_auctions = get_auctions(users)
    server_auctions = get_server_auctions(analytics_cache_ref)
    combined = user_auctions + server_auctions
    combined.sort(key=lambda x: x.get('end_at', 0))
    return combined


def place_bid_server_auction(users, save_users_func, bidder, auction_id, bid_amount, analytics_cache_ref, save_analytics_func):
    if bidder not in users:
        return False, '用户不存在'
    if not analytics_cache_ref or 'server_auctions' not in analytics_cache_ref:
        return False, '拍卖不存在'
    target_auction = analytics_cache_ref['server_auctions'].get(auction_id)
    if not target_auction:
        return False, '拍卖不存在或已结束'
    if target_auction.get('status') != 'active':
        return False, '拍卖已结束'
    now_ms = int(time.time() * 1000)
    if target_auction.get('end_at', 0) < now_ms:
        return False, '拍卖已结束'
    current_bid = target_auction.get('current_bid', 0)
    min_bid = current_bid + 10
    if bid_amount < min_bid:
        return False, f'出价必须高于当前价 {current_bid} G币，最低 {min_bid} G币'
    bidder_data = users[bidder]
    if 'gcoins' not in bidder_data or bidder_data['gcoins'].get('balance', 0) < bid_amount:
        return False, f'G币余额不足，需要 {bid_amount} G币'
    prev_bidder = target_auction.get('current_bidder', '')
    prev_bid = target_auction.get('current_bid', 0)
    if prev_bidder and prev_bidder in users:
        prev_data = users[prev_bidder]
        if 'gcoins' not in prev_data:
            prev_data['gcoins'] = {'balance': 0, 'total_earned': 0, 'total_spent': 0}
        prev_data['gcoins']['balance'] = prev_data['gcoins'].get('balance', 0) + prev_bid
        prev_data['gcoins']['total_spent'] = max(0, prev_data['gcoins'].get('total_spent', 0) - prev_bid)
    bidder_data['gcoins']['balance'] = bidder_data['gcoins'].get('balance', 0) - bid_amount
    bidder_data['gcoins']['total_spent'] = bidder_data['gcoins'].get('total_spent', 0) + bid_amount
    target_auction['current_bid'] = bid_amount
    target_auction['current_bidder'] = bidder
    if 'bids' not in target_auction:
        target_auction['bids'] = []
    target_auction['bids'].append({
        'bidder': bidder,
        'amount': bid_amount,
        'timestamp': now_ms
    })
    save_users_func()
    if save_analytics_func:
        save_analytics_func()
    return True, f'出价成功！当前最高价 {bid_amount} G币'


def settle_server_auction(users, save_users_func, auction_id, analytics_cache_ref, save_analytics_func, mail_attachments_ref=None, save_mail_func=None):
    if not analytics_cache_ref or 'server_auctions' not in analytics_cache_ref:
        return False, '拍卖不存在', 0
    target_auction = analytics_cache_ref['server_auctions'].get(auction_id)
    if not target_auction:
        return False, '拍卖不存在', 0
    if target_auction.get('status') != 'active':
        return False, '拍卖状态异常', 0
    now_ms = int(time.time() * 1000)
    if target_auction.get('end_at', 0) > now_ms:
        return False, '拍卖尚未结束', 0
    winner = target_auction.get('current_bidder', '')
    final_price = target_auction.get('current_bid', 0)
    if not winner:
        target_auction['status'] = 'unsold'
        target_auction['settled_at'] = now_ms
        if save_analytics_func:
            save_analytics_func()
        return True, '拍卖无人出价，已流拍', 0
    if winner not in users:
        target_auction['status'] = 'failed'
        target_auction['settled_at'] = now_ms
        if save_analytics_func:
            save_analytics_func()
        return False, '买家不存在', 0
    winner_data = users[winner]
    game_id = target_auction.get('game_id', '')
    card_id = target_auction.get('card_id', '')
    if 'card_collection' not in winner_data:
        winner_data['card_collection'] = {}
    if game_id not in winner_data['card_collection']:
        winner_data['card_collection'][game_id] = {}
    winner_data['card_collection'][game_id][card_id] = winner_data['card_collection'][game_id].get(card_id, 0) + 1
    winner_stats = winner_data.get('game_stats', {})
    if 'auction_wins' not in winner_stats:
        winner_stats['auction_wins'] = 0
    winner_stats['auction_wins'] += 1
    if mail_attachments_ref is not None:
        mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        mail_attachments_ref[mail_attachment_id] = {
            'id': mail_attachment_id,
            'username': winner,
            'type': 'auction_reward',
            'card_data': {
                'game_id': game_id,
                'card_id': card_id,
                'card_name': target_auction.get('card_name', ''),
                'card_emoji': target_auction.get('card_emoji', ''),
                'rarity': target_auction.get('rarity', 'legendary')
            },
            'used': False,
            'created_at': now_ms,
            'expires_at': now_ms + 7 * 24 * 3600 * 1000,
            'title': f'🔨 拍卖所得-{target_auction.get("card_name", "")}',
            'description': f'你以 {final_price} G币赢得传说卡 {target_auction.get("card_emoji", "")} {target_auction.get("card_name", "")}',
            'claimed': True,
            'claimed_at': now_ms,
            'source': 'auction_win'
        }
        if save_mail_func:
            save_mail_func()
    target_auction['status'] = 'sold'
    target_auction['settled_at'] = now_ms
    target_auction['winner'] = winner
    target_auction['final_price'] = final_price
    target_auction['system_fee'] = 0
    save_users_func()
    if save_analytics_func:
        save_analytics_func()
    return True, f'拍卖成交！{winner} 以 {final_price} G币赢得 {target_auction.get("card_name", "")}', final_price


def server_generate_random_auction(analytics_cache_ref, save_analytics_func):
    legendary_cards = get_all_legendary_cards()
    if not legendary_cards:
        return False, '没有可拍卖的传说卡', None
    if 'server_auctions' not in analytics_cache_ref:
        analytics_cache_ref['server_auctions'] = {}
    now_ms = int(time.time() * 1000)
    active_count = 0
    for auc in analytics_cache_ref['server_auctions'].values():
        if auc.get('status') == 'active' and auc.get('end_at', 0) > now_ms:
            active_count += 1
    if active_count >= 3:
        return False, '当前已有3场进行中的服务器拍卖', None
    selected = random.choice(legendary_cards)
    base_price = random.randint(100, 500)
    duration_hours = random.choice([12, 24, 36, 48])
    return server_create_auction(selected['game_id'], selected['card_id'], base_price, duration_hours, analytics_cache_ref, save_analytics_func)


def auto_settle_server_auctions(users, save_users_func, analytics_cache_ref, save_analytics_func, mail_attachments_ref=None, save_mail_func=None):
    if not analytics_cache_ref or 'server_auctions' not in analytics_cache_ref:
        return 0
    now_ms = int(time.time() * 1000)
    settled_count = 0
    for auc_id in list(analytics_cache_ref['server_auctions'].keys()):
        auc = analytics_cache_ref['server_auctions'][auc_id]
        if auc.get('status') != 'active':
            continue
        if auc.get('end_at', 0) <= now_ms:
            success, message, final_price = settle_server_auction(users, save_users_func, auc_id, analytics_cache_ref, save_analytics_func, mail_attachments_ref, save_mail_func)
            if success:
                settled_count += 1
    return settled_count


def should_create_new_auction(analytics_cache_ref, save_analytics_func, interval_hours=6):
    if not analytics_cache_ref:
        return False
    if 'last_auto_auction_time' not in analytics_cache_ref:
        analytics_cache_ref['last_auto_auction_time'] = 0
    now_ms = int(time.time() * 1000)
    interval_ms = interval_hours * 3600 * 1000
    last_time = analytics_cache_ref.get('last_auto_auction_time', 0)
    if now_ms - last_time >= interval_ms:
        analytics_cache_ref['last_auto_auction_time'] = now_ms
        if save_analytics_func:
            save_analytics_func()
        return True
    return False


class GameManager:
    def __init__(self, users_data, save_users_func, add_points_func, get_user_data_func):
        self.users = users_data
        self.save_users = save_users_func
        self.add_points = add_points_func
        self.get_user_data = get_user_data_func
        self.games = {
            'dice': self.play_dice,
            'blackjack': self.play_blackjack,
            'guess_number': self.play_guess_number,
            'rock_paper_scissors': self.play_rps,
            'roulette': self.play_roulette,
            'lucky_wheel': self.play_lucky_wheel,
            'memory_cards': self.play_memory_cards,
            'whack_mole': self.play_whack_mole,
            'dice_royale': self.play_dice_royale,
            'blackjack_tournament': self.play_blackjack_tournament,
            'treasure_hunt': self.play_treasure_hunt,
            'boss_battle': self.play_boss_battle
        }
        self.game_names = {
            'dice': '骰子大战',
            'blackjack': '二十一点',
            'guess_number': '猜数字',
            'rock_paper_scissors': '石头剪刀布',
            'roulette': '轮盘赌',
            'lucky_wheel': '幸运转盘',
            'memory_cards': '记忆翻牌',
            'whack_mole': '打地鼠',
            'dice_royale': '骰子王者',
            'blackjack_tournament': '21点锦标赛',
            'treasure_hunt': '寻宝迷宫',
            'boss_battle': '挑战BOSS'
        }
        self.guess_game_state = {}
        self.rps_game_state = {}
        self.memory_game_state = {}
        self.whack_game_state = {}
        self.current_game_state = {}

    def get_today(self):
        return datetime.now().strftime('%Y-%m-%d')

    def get_user_game_stats(self, username):
        if username not in self.users:
            return None
        user_data = self.users[username]
        if 'game_stats' not in user_data:
            user_data['game_stats'] = {
                'today_plays': 0, 'today_date': '', 'today_wins': 0, 'today_points': 0,
                'total_wins': 0, 'total_plays': 0, 'total_points_earned': 0,
                'game_wins': {}, 'game_plays': {},
                'roulette_number_hits': 0, 'memory_perfect': 0,
                'lucky_x20': 0, 'whack_score_30': 0,
                'membership_coupon_count': 0, 'membership_coupon_used': 0,
                'market_trades': 0, 'auction_wins': 0
            }
        stats = user_data['game_stats']
        today = self.get_today()
        if stats.get('today_date') != today:
            stats['today_plays'] = 0
            stats['today_wins'] = 0
            stats['today_points'] = 0
            stats['today_date'] = today
            user_data['bonus_plays'] = 0
        if 'today_wins' not in stats:
            stats['today_wins'] = 0
        if 'today_points' not in stats:
            stats['today_points'] = 0
        if 'total_points_earned' not in stats:
            stats['total_points_earned'] = 0
        if 'game_wins' not in stats:
            stats['game_wins'] = {}
        if 'game_plays' not in stats:
            stats['game_plays'] = {}
        if 'roulette_number_hits' not in stats:
            stats['roulette_number_hits'] = 0
        if 'memory_perfect' not in stats:
            stats['memory_perfect'] = 0
        if 'lucky_x20' not in stats:
            stats['lucky_x20'] = 0
        if 'whack_score_30' not in stats:
            stats['whack_score_30'] = 0
        if 'membership_coupon_count' not in stats:
            stats['membership_coupon_count'] = 0
        if 'membership_coupon_used' not in stats:
            stats['membership_coupon_used'] = 0
        if 'market_trades' not in stats:
            stats['market_trades'] = 0
        if 'auction_wins' not in stats:
            stats['auction_wins'] = 0
        return stats

    def get_user_game_history(self, username):
        if username not in self.users:
            return []
        user_data = self.users[username]
        if 'game_history' not in user_data:
            user_data['game_history'] = []
        return user_data['game_history']

    def add_game_history(self, username, game_id, won, points_earned, detail=''):
        if username not in self.users:
            return
        user_data = self.users[username]
        if 'game_history' not in user_data:
            user_data['game_history'] = []
        record = {
            'id': f"{int(time.time()*1000)}_{random.randint(1000,9999)}",
            'game_id': game_id,
            'game_name': self.game_names.get(game_id, game_id),
            'won': won,
            'points_earned': points_earned,
            'detail': detail,
            'timestamp': int(time.time() * 1000)
        }
        user_data['game_history'].insert(0, record)
        if len(user_data['game_history']) > 50:
            user_data['game_history'] = user_data['game_history'][:50]
        self.save_users()

    def clear_game_history(self, username):
        if username not in self.users:
            return False
        user_data = self.users[username]
        user_data['game_history'] = []
        self.save_users()
        return True

    def delete_game_history_item(self, username, record_id):
        if username not in self.users:
            return False
        user_data = self.users[username]
        if 'game_history' not in user_data:
            return False
        original = len(user_data['game_history'])
        user_data['game_history'] = [r for r in user_data['game_history'] if r.get('id') != record_id]
        if len(user_data['game_history']) == original:
            return False
        self.save_users()
        return True

    def get_win_streak(self, username):
        if username not in self.users:
            return {'current_win': 0, 'current_lose': 0, 'max_win': 0, 'max_lose': 0}
        user_data = self.users[username]
        if 'win_streak' not in user_data:
            user_data['win_streak'] = {'current_win': 0, 'current_lose': 0, 'max_win': 0, 'max_lose': 0}
        if 'max_lose' not in user_data['win_streak']:
            user_data['win_streak']['max_lose'] = 0
        return user_data['win_streak']

    def update_win_streak(self, username, won):
        if username not in self.users:
            return {'current_win': 0, 'current_lose': 0, 'max_win': 0, 'max_lose': 0, 'bonus_rate': 0, 'bonus_message': ''}
        user_data = self.users[username]
        if 'win_streak' not in user_data:
            user_data['win_streak'] = {'current_win': 0, 'current_lose': 0, 'max_win': 0, 'max_lose': 0}
        ws = user_data['win_streak']
        if 'max_lose' not in ws:
            ws['max_lose'] = 0
        if won:
            ws['current_win'] = ws.get('current_win', 0) + 1
            ws['current_lose'] = 0
            if ws['current_win'] > ws.get('max_win', 0):
                ws['max_win'] = ws['current_win']
        else:
            ws['current_lose'] = ws.get('current_lose', 0) + 1
            ws['current_win'] = 0
            if ws['current_lose'] > ws.get('max_lose', 0):
                ws['max_lose'] = ws['current_lose']
        bonus_rate = 0
        bonus_message = ''
        if ws['current_win'] >= 5:
            bonus_rate = 0.5
            bonus_message = f'🔥 连赢{ws["current_win"]}局！额外+50% G币'
        elif ws['current_win'] >= 3:
            bonus_rate = 0.2
            bonus_message = f'🔥 连赢{ws["current_win"]}局！额外+20% G币'
        if not won and ws['current_lose'] >= 3:
            bonus_message = f'💪 连败{ws["current_lose"]}局，下次胜利有安慰奖励'
        self.save_users()
        return {
            'current_win': ws['current_win'],
            'current_lose': ws['current_lose'],
            'max_win': ws.get('max_win', 0),
            'max_lose': ws.get('max_lose', 0),
            'bonus_rate': bonus_rate,
            'bonus_message': bonus_message
        }

    def get_daily_tasks(self, username):
        if username not in self.users:
            return {'tasks': [], 'completed_count': 0, 'total_count': 0, 'all_completed': False, 'bonus_claimed': False}
        user_data = self.users[username]
        today = self.get_today()
        if 'daily_tasks' not in user_data or user_data['daily_tasks'].get('date') != today:
            selected = random.sample(DAILY_TASK_POOL, min(3, len(DAILY_TASK_POOL)))
            user_data['daily_tasks'] = {
                'date': today,
                'tasks': [
                    {'id': t['id'], 'name': t['name'], 'type': t['type'], 'target': t['target'],
                     'reward': t['reward'], 'game': t.get('game', ''), 'progress': 0, 'claimed': False}
                    for t in selected
                ],
                'bonus_claimed': False
            }
            self.save_users()
        tasks = user_data['daily_tasks']['tasks']
        completed_count = sum(1 for t in tasks if t['progress'] >= t['target'])
        return {
            'tasks': tasks,
            'completed_count': completed_count,
            'total_count': len(tasks),
            'all_completed': completed_count >= len(tasks),
            'bonus_claimed': user_data['daily_tasks'].get('bonus_claimed', False)
        }

    def update_daily_tasks(self, username, game_id, won, extra=None):
        if username not in self.users:
            return
        user_data = self.users[username]
        today = self.get_today()
        if 'daily_tasks' not in user_data or user_data['daily_tasks'].get('date') != today:
            self.get_daily_tasks(username)
        tasks = user_data['daily_tasks']['tasks']
        extra = extra or {}
        ws = self.get_win_streak(username)
        for task in tasks:
            if task['progress'] >= task['target']:
                continue
            ttype = task['type']
            if ttype == 'play_count':
                task['progress'] = min(task['target'], task['progress'] + 1)
            elif ttype == 'win_count':
                if won:
                    task['progress'] = min(task['target'], task['progress'] + 1)
            elif ttype == 'game_specific':
                if task.get('game') == game_id:
                    task['progress'] = min(task['target'], task['progress'] + 1)
            elif ttype == 'win_streak':
                if won:
                    current_streak = ws.get('current_win', 0)
                    if current_streak >= task['target']:
                        task['progress'] = task['target']
                    else:
                        task['progress'] = current_streak
                else:
                    if task['progress'] < task['target']:
                        task['progress'] = 0
            elif ttype == 'guess_fast':
                if game_id == 'guess_number' and extra.get('attempts', 999) <= 5 and won:
                    task['progress'] = task['target']
            elif ttype == 'roulette_win':
                if game_id == 'roulette' and won:
                    task['progress'] = min(task['target'], task['progress'] + 1)
        self.save_users()

    def claim_daily_task(self, username, task_id):
        if username not in self.users:
            return False, '用户不存在'
        user_data = self.users[username]
        today = self.get_today()
        if 'daily_tasks' not in user_data or user_data['daily_tasks'].get('date') != today:
            return False, '今日任务未生成'
        for task in user_data['daily_tasks']['tasks']:
            if task['id'] == task_id:
                if task['progress'] < task['target']:
                    return False, '任务未完成'
                if task['claimed']:
                    return False, '任务已领取'
                task['claimed'] = True
                reward = task['reward']
                self.add_points(username, reward)
                add_gcoins(self.users, username, reward * 5, 'daily_task')
                self.save_users()
                return True, f'领取成功！获得{reward}积分 + {reward*5}G币'
        return False, '任务不存在'

    def claim_all_daily_tasks(self, username):
        if username not in self.users:
            return False, '用户不存在', 0
        user_data = self.users[username]
        today = self.get_today()
        if 'daily_tasks' not in user_data or user_data['daily_tasks'].get('date') != today:
            return False, '今日任务未生成', 0
        all_tasks = user_data['daily_tasks']['tasks']
        already_claimed_all_before = all(t['claimed'] for t in all_tasks)
        total_reward = 0
        claimed_count = 0
        for task in all_tasks:
            if task['progress'] >= task['target'] and not task['claimed']:
                task['claimed'] = True
                total_reward += task['reward']
                claimed_count += 1
        if claimed_count == 0:
            return False, '没有可领取的任务', 0
        just_completed_all = all(t['claimed'] for t in all_tasks) and not already_claimed_all_before
        if just_completed_all and not user_data['daily_tasks'].get('bonus_claimed', False):
            tier_bonus = get_member_daily_task_bonus(self.users, username)
            extra_bonus = 15 + tier_bonus
            total_reward += extra_bonus
            user_data['daily_tasks']['bonus_claimed'] = True
        self.add_points(username, total_reward)
        add_gcoins(self.users, username, total_reward * 5, 'daily_task_all')
        self.save_users()
        return True, f'领取成功！共获得{total_reward}积分', total_reward

    def get_user_cards(self, username):
        if username not in self.users:
            return {}
        user_data = self.users[username]
        if 'card_collection' not in user_data:
            user_data['card_collection'] = {}
        return user_data['card_collection']

    def get_collection_overview(self, username):
        cards = self.get_user_cards(username)
        game_progress = {}
        total_owned = 0
        total_count = 0
        for game_id, collection in CARD_COLLECTIONS.items():
            owned = cards.get(game_id, {})
            game_total = len(collection['cards'])
            game_owned = len(owned)
            total_owned += game_owned
            total_count += game_total
            game_progress[game_id] = {
                'name': collection['name'],
                'icon': collection['icon'],
                'owned': game_owned,
                'total': game_total,
                'complete': game_owned >= game_total,
                'cards': []
            }
            for card in collection['cards']:
                owned_count = owned.get(card['id'], 0)
                game_progress[game_id]['cards'].append({
                    'id': card['id'],
                    'name': card['name'],
                    'emoji': card['emoji'],
                    'rarity': card['rarity'],
                    'rarity_name': CARD_RARITY_NAMES[card['rarity']],
                    'rarity_color': CARD_RARITY_COLORS[card['rarity']],
                    'owned': owned_count > 0,
                    'count': owned_count
                })
        return {
            'game_progress': game_progress,
            'total_owned': total_owned,
            'total_count': total_count,
            'progress_percent': round(total_owned / max(1, total_count) * 100, 1)
        }

    def get_disenchantable_cards(self, username):
        cards = self.get_user_cards(username)
        result = []
        for game_id, collection in CARD_COLLECTIONS.items():
            owned = cards.get(game_id, {})
            for card in collection['cards']:
                count = owned.get(card['id'], 0)
                if count > 1:
                    result.append({
                        'game_id': game_id,
                        'game_name': collection['name'],
                        'card_id': card['id'],
                        'card_name': card['name'],
                        'emoji': card['emoji'],
                        'rarity': card['rarity'],
                        'rarity_name': CARD_RARITY_NAMES[card['rarity']],
                        'rarity_color': CARD_RARITY_COLORS[card['rarity']],
                        'count': count,
                        'extra': count - 1,
                        'disenchant_value': CARD_RARITY_DISENCHANT[card['rarity']],
                        'total_value': (count - 1) * CARD_RARITY_DISENCHANT[card['rarity']]
                    })
        return result

    def disenchant_all_duplicates(self, username, max_details=100):
        if username not in self.users:
            return False, '用户不存在', 0, [], 0
        user_data = self.users[username]
        if 'card_collection' not in user_data:
            return False, '没有可分解的卡牌', 0, [], 0
        cards = user_data['card_collection']
        total_points = 0
        details = []
        total_cards_disenchanted = 0
        for game_id, collection in CARD_COLLECTIONS.items():
            owned = cards.get(game_id, {})
            for card in collection['cards']:
                count = owned.get(card['id'], 0)
                if count > 1:
                    extra = count - 1
                    value = extra * CARD_RARITY_DISENCHANT[card['rarity']]
                    total_points += value
                    total_cards_disenchanted += extra
                    owned[card['id']] = 1
                    if len(details) < max_details:
                        details.append({
                            'game_id': game_id,
                            'card_id': card['id'],
                            'card_name': card['name'],
                            'emoji': card['emoji'],
                            'rarity_name': CARD_RARITY_NAMES[card['rarity']],
                            'rarity_color': CARD_RARITY_COLORS[card['rarity']],
                            'extra': extra,
                            'points': value
                        })
        if total_points <= 0:
            return False, '没有可分解的重复卡牌', 0, [], 0
        self.add_points(username, total_points)
        add_gcoins(self.users, username, total_points * 10, 'disenchant')
        self.save_users()
        truncated = len(details) >= max_details and total_cards_disenchanted > max_details
        return True, f'一键分解成功！共分解{total_cards_disenchanted}张重复卡牌，获得{total_points}积分 + {total_points*10}G币', total_points, details, total_cards_disenchanted

    def roll_card_drop(self, username, game_id):
        if game_id not in CARD_COLLECTIONS:
            return None
        user_data = self.users[username]
        drop_chance = 0.30
        if is_game_member(self.users, username):
            drop_chance += 0.20
        effects = self.get_active_effects(username)
        if 'member_double_drop' in effects:
            drop_chance *= 2
        if random.random() > drop_chance:
            return None
        cards_pool = CARD_COLLECTIONS[game_id]['cards']
        rarity_weights = [CARD_DROP_RATES[card['rarity']] for card in cards_pool]
        total_weight = sum(rarity_weights)
        if total_weight <= 0:
            return None
        rand = random.uniform(0, total_weight)
        cumulative = 0
        selected = cards_pool[-1]
        for i, card in enumerate(cards_pool):
            cumulative += rarity_weights[i]
            if rand <= cumulative:
                selected = card
                break
        if 'card_collection' not in user_data:
            user_data['card_collection'] = {}
        if game_id not in user_data['card_collection']:
            user_data['card_collection'][game_id] = {}
        owned = user_data['card_collection'][game_id]
        is_new = selected['id'] not in owned
        if is_new:
            owned[selected['id']] = 1
        else:
            owned[selected['id']] = owned[selected['id']] + 1
        self.save_users()
        self._check_and_unlock_achievements(username)
        if is_new:
            return {
                'type': 'card',
                'is_new': True,
                'card': selected,
                'rarity_name': CARD_RARITY_NAMES[selected['rarity']],
                'rarity_color': CARD_RARITY_COLORS[selected['rarity']],
                'message': f'🎉 获得新卡牌 {selected["emoji"]} {selected["name"]}（{CARD_RARITY_NAMES[selected["rarity"]]}）'
            }
        else:
            disenchant = CARD_RARITY_DISENCHANT[selected['rarity']]
            self.add_points(username, disenchant)
            add_gcoins(self.users, username, disenchant * 10, 'card_duplicate')
            return {
                'type': 'card',
                'is_new': False,
                'card': selected,
                'rarity_name': CARD_RARITY_NAMES[selected['rarity']],
                'rarity_color': CARD_RARITY_COLORS[selected['rarity']],
                'disenchant_points': disenchant,
                'message': f'🎴 重复卡牌 {selected["emoji"]} {selected["name"]}，自动分解为 {disenchant} 积分'
            }

    def roll_coupon_drop(self, username, game_id):
        if is_game_member(self.users, username):
            return None
        base_rate = 0.08
        win_streak = self.get_win_streak(username)
        current_win = win_streak.get('current_win', 0)
        if current_win >= 5:
            base_rate *= 3
        elif current_win >= 3:
            base_rate *= 2
        if game_id in ['roulette', 'lucky_wheel']:
            base_rate *= 1.5
        effects = self.get_active_effects(username)
        if 'member_double_coupon' in effects:
            base_rate *= 2
        if random.random() > base_rate:
            return None
        total_weight = sum(c['weight'] for c in COUPON_DROP_TABLE)
        rand = random.uniform(0, total_weight)
        cumulative = 0
        selected = COUPON_DROP_TABLE[-1]
        for c in COUPON_DROP_TABLE:
            cumulative += c['weight']
            if rand <= cumulative:
                selected = c
                break
        user_data = self.users[username]
        if 'membership_coupons' not in user_data:
            user_data['membership_coupons'] = {}
        coupon_id = f"mc_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        now_ms = int(time.time() * 1000)
        user_data['membership_coupons'][coupon_id] = {
            'id': coupon_id,
            'discount': selected['discount'],
            'used': False,
            'expire_at': now_ms + MEMBERSHIP_COUPON_EXPIRE_DAYS * 24 * 3600 * 1000,
            'created_at': now_ms,
            'description': selected['desc'],
            'source': 'game_drop'
        }
        stats = self.get_user_game_stats(username)
        stats['membership_coupon_count'] = stats.get('membership_coupon_count', 0) + 1
        self.save_users()
        self._check_and_unlock_achievements(username)
        return {
            'type': 'membership_coupon',
            'discount': selected['discount'],
            'desc': selected['desc'],
            'coupon_id': coupon_id,
            'expire_at': user_data['membership_coupons'][coupon_id]['expire_at'],
            'message': f'🎟️ 恭喜获得会员优惠券！{selected["desc"]}'
        }

    def roll_item_drop(self, username, game_id):
        base_rate = 0.02
        if is_game_member(self.users, username):
            base_rate *= 1.5
        if random.random() > base_rate:
            return None
        basic_items = [i for i in ITEM_SHOP.values() if not i.get('member_only', False)]
        if not basic_items:
            return None
        selected = random.choice(basic_items)
        user_data = self.users[username]
        if 'items' not in user_data:
            user_data['items'] = {}
        if selected['id'] not in user_data['items']:
            user_data['items'][selected['id']] = {
                'id': selected['id'],
                'name': selected['name'],
                'icon': selected['icon'],
                'desc': selected['desc'],
                'count': 0,
                'expires_at': 0
            }
        user_data['items'][selected['id']]['count'] = user_data['items'][selected['id']].get('count', 0) + 1
        if user_data['items'][selected['id']]['count'] > 99:
            user_data['items'][selected['id']]['count'] = 99
        self.save_users()
        return {
            'type': 'item',
            'item_id': selected['id'],
            'name': selected['name'],
            'icon': selected['icon'],
            'message': f'{selected["icon"]} 恭喜获得道具 {selected["name"]} x1！'
        }

    def roll_points_bonus(self, username, game_id):
        base_rate = 0.01
        if is_game_member(self.users, username):
            base_rate *= 1.5
        if random.random() > base_rate:
            return None
        total_weight = sum(c['weight'] for c in POINTS_BONUS_TABLE)
        rand = random.uniform(0, total_weight)
        cumulative = 0
        selected = POINTS_BONUS_TABLE[-1]
        for c in POINTS_BONUS_TABLE:
            cumulative += c['weight']
            if rand <= cumulative:
                selected = c
                break
        self.add_points(username, selected['amount'])
        add_gcoins(self.users, username, int(selected['amount'] * 10), 'points_bonus')
        return {
            'type': 'points_bonus',
            'amount': selected['amount'],
            'message': f'🧧 恭喜获得 {selected["amount"]} 积分红包 + {int(selected["amount"] * 10)} G币！'
        }

    def roll_gcoin_drop(self, username, game_id):
        base_rate = 0.15
        if is_game_member(self.users, username):
            base_rate *= 2
        if random.random() > base_rate:
            return None
        gcoin_amount = random.randint(5, 50)
        add_gcoins(self.users, username, gcoin_amount, 'game_drop')
        return {
            'type': 'gcoin',
            'amount': gcoin_amount,
            'message': f'🪙 恭喜获得 {gcoin_amount} G币！'
        }

    def roll_all_drops(self, username, game_id, won):
        drops = []
        if not won:
            return drops
        card_drop = self.roll_card_drop(username, game_id)
        if card_drop:
            drops.append(card_drop)
        coupon_drop = self.roll_coupon_drop(username, game_id)
        if coupon_drop:
            drops.append(coupon_drop)
        item_drop = self.roll_item_drop(username, game_id)
        if item_drop:
            drops.append(item_drop)
        points_drop = self.roll_points_bonus(username, game_id)
        if points_drop:
            drops.append(points_drop)
        gcoin_drop = self.roll_gcoin_drop(username, game_id)
        if gcoin_drop:
            drops.append(gcoin_drop)
        return drops

    def disenchant_card(self, username, game_id, card_id):
        if username not in self.users:
            return False, '用户不存在', 0
        user_data = self.users[username]
        if 'card_collection' not in user_data:
            return False, '未拥有该卡牌', 0
        if game_id not in user_data['card_collection']:
            return False, '未拥有该卡牌', 0
        owned = user_data['card_collection'][game_id]
        if card_id not in owned:
            return False, '未拥有该卡牌', 0
        if owned[card_id] <= 1:
            return False, '至少保留1张卡牌', 0
        card_info = None
        for card in CARD_COLLECTIONS[game_id]['cards']:
            if card['id'] == card_id:
                card_info = card
                break
        if not card_info:
            return False, '卡牌不存在', 0
        disenchant = CARD_RARITY_DISENCHANT[card_info['rarity']]
        owned[card_id] = owned[card_id] - 1
        self.add_points(username, disenchant)
        add_gcoins(self.users, username, disenchant * 10, 'disenchant')
        self.save_users()
        return True, f'分解成功！获得{disenchant}积分 + {disenchant*10}G币', disenchant

    def _compute_achievement_progress(self, ach, stats, win_streak, tier, checkin, chest, daily_first, total_cards, sets_complete, username):
        progress = 0
        if ach['type'] == 'total_plays':
            progress = stats.get('total_plays', 0)
        elif ach['type'] == 'total_wins':
            progress = stats.get('total_wins', 0)
        elif ach['type'] == 'max_win_streak':
            progress = win_streak.get('max_win', 0)
        elif ach['type'] == 'max_lose_streak':
            progress = win_streak.get('max_lose', 0)
        elif ach['type'].startswith('game_wins_'):
            game_id = ach['type'].replace('game_wins_', '')
            progress = stats.get('game_wins', {}).get(game_id, 0)
        elif ach['type'] == 'roulette_number_hits':
            progress = stats.get('roulette_number_hits', 0)
        elif ach['type'] == 'memory_perfect':
            progress = stats.get('memory_perfect', 0)
        elif ach['type'] == 'total_points_earned':
            progress = int(stats.get('total_points_earned', 0))
        elif ach['type'] == 'is_member':
            progress = 1 if is_game_member(self.users, username) else 0
        elif ach['type'] == 'is_gold':
            progress = 1 if _get_base_tier(tier) == 'gold' else 0
        elif ach['type'] == 'is_diamond':
            progress = 1 if _get_base_tier(tier) == 'diamond' else 0
        elif ach['type'] == 'is_supreme':
            progress = 1 if _get_base_tier(tier) == 'supreme' else 0
        elif ach['type'] == 'lucky_x20':
            progress = stats.get('lucky_x20', 0)
        elif ach['type'] == 'checkin_streak':
            progress = checkin.get('consecutive_days', 0)
        elif ach['type'] == 'checkin_total':
            progress = checkin.get('total_days', 0)
        elif ach['type'] == 'chest_full':
            progress = 1 if chest.get('all_opened', False) else 0
        elif ach['type'] == 'daily_first_win':
            progress = 1 if daily_first.get('total_claimed', 0) > 0 else 0
        elif ach['type'] == 'cards_total':
            progress = total_cards
        elif ach['type'].startswith('cards_set_'):
            game_id = ach['type'].replace('cards_set_', '')
            progress = 1 if sets_complete.get(game_id, False) else 0
        elif ach['type'] == 'whack_score_30':
            progress = stats.get('whack_score_30', 0)
        elif ach['type'] == 'membership_coupon_count':
            progress = stats.get('membership_coupon_count', 0)
        elif ach['type'] == 'membership_coupon_used':
            progress = stats.get('membership_coupon_used', 0)
        elif ach['type'] == 'gcoins_total':
            gcoin_data = get_gcoin_data(self.users, username)
            progress = gcoin_data.get('total_earned', 0) if gcoin_data else 0
        elif ach['type'] == 'market_trades':
            progress = stats.get('market_trades', 0)
        elif ach['type'] == 'auction_wins':
            progress = stats.get('auction_wins', 0)
        return progress

    def _check_and_unlock_achievements(self, username):
        if username not in self.users:
            return
        user_data = self.users[username]
        if 'achievements' not in user_data:
            user_data['achievements'] = {}
        unlocked = user_data['achievements']
        stats = self.get_user_game_stats(username)
        if not stats:
            return
        win_streak = self.get_win_streak(username)
        tier = get_member_tier(self.users, username)
        checkin = self.get_checkin_status(username)
        chest = self.get_chest_status(username)
        daily_first = self.get_daily_first_win_status(username)
        cards = self.get_user_cards(username)
        total_cards = 0
        sets_complete = {}
        for game_id, collection in CARD_COLLECTIONS.items():
            owned = cards.get(game_id, {})
            game_total = len(collection['cards'])
            game_owned = len(owned)
            total_cards += game_owned
            sets_complete[game_id] = game_owned >= game_total
        changed = False
        for ach in ACHIEVEMENTS:
            if ach['id'] in unlocked:
                continue
            progress = self._compute_achievement_progress(ach, stats, win_streak, tier, checkin, chest, daily_first, total_cards, sets_complete, username)
            if progress >= ach['target']:
                unlocked[ach['id']] = {'unlocked_at': int(time.time() * 1000), 'reward_claimed': False}
                add_gcoins(self.users, username, GCOIN_EARN_TABLE['achievement_unlock'], 'achievement_unlock')
                changed = True
        if changed:
            self.save_users()

    def get_achievements(self, username, unlock=True):
        if username not in self.users:
            return {'achievements': [], 'unlocked_count': 0, 'total_count': len(ACHIEVEMENTS)}
        if unlock:
            self._check_and_unlock_achievements(username)
        user_data = self.users[username]
        if 'achievements' not in user_data:
            user_data['achievements'] = {}
        unlocked = user_data['achievements']
        stats = self.get_user_game_stats(username)
        win_streak = self.get_win_streak(username)
        tier = get_member_tier(self.users, username)
        checkin = self.get_checkin_status(username)
        chest = self.get_chest_status(username)
        daily_first = self.get_daily_first_win_status(username)
        cards = self.get_user_cards(username)
        total_cards = 0
        sets_complete = {}
        for game_id, collection in CARD_COLLECTIONS.items():
            owned = cards.get(game_id, {})
            game_total = len(collection['cards'])
            game_owned = len(owned)
            total_cards += game_owned
            sets_complete[game_id] = game_owned >= game_total
        result = []
        for ach in ACHIEVEMENTS:
            progress = self._compute_achievement_progress(ach, stats, win_streak, tier, checkin, chest, daily_first, total_cards, sets_complete, username)
            unlocked_status = ach['id'] in unlocked
            result.append({
                'id': ach['id'],
                'name': ach['name'],
                'desc': ach['desc'],
                'icon': ach['icon'],
                'reward': ach['reward'],
                'progress': min(progress, ach['target']),
                'target': ach['target'],
                'unlocked': unlocked_status,
                'reward_claimed': unlocked.get(ach['id'], {}).get('reward_claimed', False) if unlocked_status else False,
                'unlocked_at': unlocked.get(ach['id'], {}).get('unlocked_at', 0) if unlocked_status else 0
            })
        unlocked_count = sum(1 for a in result if a['unlocked'])
        return {'achievements': result, 'unlocked_count': unlocked_count, 'total_count': len(ACHIEVEMENTS)}

    def claim_achievement_reward(self, username, achievement_id):
        if username not in self.users:
            return False, '用户不存在'
        user_data = self.users[username]
        if 'achievements' not in user_data:
            return False, '暂无成就'
        ach_data = user_data['achievements'].get(achievement_id)
        if not ach_data:
            return False, '成就未解锁'
        if ach_data.get('reward_claimed', False):
            return False, '奖励已领取'
        ach_info = None
        for a in ACHIEVEMENTS:
            if a['id'] == achievement_id:
                ach_info = a
                break
        if not ach_info:
            return False, '成就不存在'
        ach_data['reward_claimed'] = True
        reward = ach_info['reward']
        self.add_points(username, reward)
        add_gcoins(self.users, username, reward * 10, 'achievement_reward')
        self.save_users()
        return True, f'领取成功！获得{reward}积分 + {reward*10}G币'

    def claim_all_achievement_rewards(self, username):
        if username not in self.users:
            return False, '用户不存在', 0
        user_data = self.users[username]
        if 'achievements' not in user_data:
            return False, '暂无可领取', 0
        total_reward = 0
        count = 0
        for ach_id, ach_data in user_data['achievements'].items():
            if not ach_data.get('reward_claimed', False):
                ach_info = None
                for a in ACHIEVEMENTS:
                    if a['id'] == ach_id:
                        ach_info = a
                        break
                if ach_info:
                    ach_data['reward_claimed'] = True
                    total_reward += ach_info['reward']
                    count += 1
        if count == 0:
            return False, '没有可领取的成就奖励', 0
        self.add_points(username, total_reward)
        add_gcoins(self.users, username, total_reward * 10, 'achievement_reward_all')
        self.save_users()
        return True, f'领取成功！共获得{total_reward}积分 + {total_reward*10}G币', total_reward

    def get_user_items(self, username):
        if username not in self.users:
            return {}
        user_data = self.users[username]
        if 'items' not in user_data:
            user_data['items'] = {}
        now = int(time.time())
        changed = False
        for item_id in list(user_data['items'].keys()):
            item = user_data['items'][item_id]
            if item.get('expires_at', 0) > 0 and item['expires_at'] < now:
                del user_data['items'][item_id]
                changed = True
        if changed:
            self.save_users()
        return user_data['items']

    def buy_item(self, username, item_id):
        if username not in self.users:
            return False, '用户不存在'
        if item_id not in ITEM_SHOP:
            return False, '道具不存在'
        item_info = ITEM_SHOP[item_id]
        if item_info.get('member_only', False):
            if not is_game_member(self.users, username):
                return False, '该道具为会员专属，请先开通会员'
            current_tier = get_member_tier(self.users, username)
            min_tier = item_info.get('min_tier', 'none')
            tier_order = {'none': 0, 'normal': 1, 'gold': 2, 'diamond': 3, 'supreme': 4}
            current_base = _get_base_tier(current_tier)
            if tier_order.get(current_base, 0) < tier_order.get(min_tier, 0):
                min_name = MEMBERSHIP_TIERS.get(min_tier, {}).get('name', min_tier)
                return False, f'该道具需要{min_name}及以上才能购买'
        user_data = self.users[username]
        price = item_info['price']
        if user_data.get('totalPoints', 0) < price:
            return False, f'积分不足，需要{price}积分'
        user_data['totalPoints'] = round(user_data['totalPoints'] - price, 2)
        if 'items' not in user_data:
            user_data['items'] = {}
        if item_id not in user_data['items']:
            user_data['items'][item_id] = {
                'id': item_id,
                'name': item_info['name'],
                'icon': item_info['icon'],
                'desc': item_info['desc'],
                'count': 0,
                'expires_at': 0
            }
        user_data['items'][item_id]['count'] = user_data['items'][item_id].get('count', 0) + 1
        if user_data['items'][item_id]['count'] > 99:
            user_data['items'][item_id]['count'] = 99
        self.save_users()
        return True, f'购买成功！获得{item_info["name"]} x1'

    def use_item(self, username, item_id):
        if username not in self.users:
            return False, '用户不存在'
        user_data = self.users[username]
        if 'items' not in user_data or item_id not in user_data['items']:
            return False, '没有该道具'
        item = user_data['items'][item_id]
        if item.get('count', 0) <= 0:
            return False, '道具数量不足'
        if item_id == 'extra_play':
            bonus = user_data.get('bonus_plays', 0)
            if bonus >= 5:
                return False, '今日次数加成已达上限（5次）'
            user_data['bonus_plays'] = bonus + 1
            item['count'] = item['count'] - 1
            if item['count'] <= 0:
                del user_data['items'][item_id]
            self.save_users()
            return True, '使用成功！今日游戏次数 +1'
        if 'active_items' not in user_data:
            user_data['active_items'] = {}
        now = int(time.time())
        duration = ITEM_SHOP.get(item_id, {}).get('duration', 300)
        user_data['active_items'][item_id] = {'expires_at': now + duration, 'used_at': now}
        item['count'] = item['count'] - 1
        if item['count'] <= 0:
            del user_data['items'][item_id]
        self.save_users()
        return True, f'{ITEM_SHOP[item_id]["name"]}已激活，{duration//60}分钟内有效'

    def get_active_effects(self, username):
        if username not in self.users:
            return {}
        user_data = self.users[username]
        if 'active_items' not in user_data:
            return {}
        now = int(time.time())
        effects = {}
        changed = False
        for item_id in list(user_data['active_items'].keys()):
            item = user_data['active_items'][item_id]
            if item.get('expires_at', 0) > now:
                effects[item_id] = item
            else:
                del user_data['active_items'][item_id]
                changed = True
        if changed:
            self.save_users()
        return effects

    def consume_effects(self, username, item_id, persist=True):
        if username not in self.users:
            return
        user_data = self.users[username]
        if 'active_items' in user_data and item_id in user_data['active_items']:
            del user_data['active_items'][item_id]
            if persist:
                self.save_users()

    def get_leaderboard(self, period='total', limit=100):
        if period == 'today':
            date_filter = self.get_today()
        elif period == 'week':
            date_filter = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        else:
            date_filter = None
        results = []
        for username, user_data in self.users.items():
            stats = user_data.get('game_stats', {})
            if period == 'today':
                today_date = stats.get('today_date', '')
                if today_date != date_filter:
                    continue
                plays = stats.get('today_plays', 0)
                wins = stats.get('today_wins', 0)
                points = stats.get('today_points', 0)
            else:
                plays = stats.get('total_plays', 0)
                wins = stats.get('total_wins', 0)
                points = int(stats.get('total_points_earned', 0))
            if plays <= 0:
                continue
            win_rate = round(wins / max(1, plays) * 100, 1)
            tier = get_member_tier(self.users, username)
            level_info = self.get_user_level(username)
            title_info = self.get_user_title(username)
            results.append({
                'username': username,
                'plays': plays,
                'wins': wins,
                'win_rate': win_rate,
                'points': points,
                'member_tier': tier,
                'level': level_info.get('level', 1),
                'level_icon': level_info.get('icon', '🌱'),
                'level_name': level_info.get('name', '新手'),
                'title': title_info.get('name', ''),
                'title_icon': title_info.get('icon', '')
            })
        results.sort(key=lambda x: (-x['wins'], -x['win_rate'], -x['points']))
        return results[:limit]

    def get_personal_stats(self, username):
        if username not in self.users:
            return None
        stats = self.get_user_game_stats(username)
        win_streak = self.get_win_streak(username)
        game_stats = {}
        for game_id, game_name in self.game_names.items():
            game_stats[game_id] = {'name': game_name, 'plays': 0, 'wins': 0, 'win_rate': 0}
        game_wins = stats.get('game_wins', {})
        game_plays = stats.get('game_plays', {})
        for game_id in game_stats:
            wins = game_wins.get(game_id, 0)
            plays = game_plays.get(game_id, 0)
            game_stats[game_id]['wins'] = wins
            game_stats[game_id]['plays'] = plays
            if plays > 0:
                game_stats[game_id]['win_rate'] = round(wins / plays * 100, 1)
        total_plays = stats.get('total_plays', 0)
        total_wins = stats.get('total_wins', 0)
        total_points = int(stats.get('total_points_earned', 0))
        level_info = self.get_user_level(username)
        title_info = self.get_user_title(username)
        gcoin_data = get_gcoin_data(self.users, username)
        return {
            'total_plays': total_plays,
            'total_wins': total_wins,
            'total_losses': max(0, total_plays - total_wins),
            'win_rate': round(total_wins / max(1, total_plays) * 100, 1),
            'total_points_earned': total_points,
            'max_win_streak': win_streak.get('max_win', 0),
            'max_lose_streak': win_streak.get('max_lose', 0),
            'current_win_streak': win_streak.get('current_win', 0),
            'current_lose_streak': win_streak.get('current_lose', 0),
            'game_stats': game_stats,
            'level_info': level_info,
            'title_info': title_info,
            'gcoins': gcoin_data
        }

    def get_checkin_status(self, username):
        if username not in self.users:
            return None
        user_data = self.users[username]
        if 'checkin' not in user_data:
            user_data['checkin'] = {'last_date': '', 'consecutive_days': 0, 'total_days': 0, 'claimed_today': False, 'history': []}
            self.save_users()
        checkin = user_data['checkin']
        today = self.get_today()
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        if checkin.get('last_date') != today:
            if checkin.get('last_date') != yesterday and checkin.get('last_date') != '':
                if checkin.get('consecutive_days', 0) > 0:
                    checkin['consecutive_days'] = 0
            checkin['claimed_today'] = False
        day_index = checkin.get('consecutive_days', 0)
        next_day = day_index + 1 if day_index < 7 else 1
        rewards = []
        for i, r in enumerate(CHECKIN_REWARDS):
            day_num = i + 1
            if checkin.get('claimed_today', False):
                status = 'claimed' if day_num <= day_index else 'pending'
            else:
                status = 'claimed' if day_num < day_index else ('current' if day_num == day_index + 1 else 'pending')
            rewards.append({'day': day_num, 'reward_type': r['reward_type'], 'value': r['value'], 'icon': r['icon'], 'desc': r['desc'], 'status': status})
        return {
            'consecutive_days': checkin.get('consecutive_days', 0),
            'total_days': checkin.get('total_days', 0),
            'claimed_today': checkin.get('claimed_today', False),
            'next_day': next_day,
            'rewards': rewards,
            'last_date': checkin.get('last_date', '')
        }

    def claim_checkin(self, username):
        if username not in self.users:
            return False, '用户不存在', None
        user_data = self.users[username]
        if 'checkin' not in user_data:
            user_data['checkin'] = {'last_date': '', 'consecutive_days': 0, 'total_days': 0, 'claimed_today': False, 'history': []}
        checkin = user_data['checkin']
        today = self.get_today()
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        if checkin.get('last_date') == today and checkin.get('claimed_today', False):
            return False, '今日已签到', None
        if checkin.get('last_date') == yesterday:
            checkin['consecutive_days'] = checkin.get('consecutive_days', 0) + 1
        else:
            checkin['consecutive_days'] = 1
        if checkin['consecutive_days'] > 7:
            checkin['consecutive_days'] = 1
        day_index = checkin['consecutive_days']
        reward = CHECKIN_REWARDS[day_index - 1]
        checkin['last_date'] = today
        checkin['claimed_today'] = True
        checkin['total_days'] = checkin.get('total_days', 0) + 1
        if 'history' not in checkin:
            checkin['history'] = []
        checkin['history'].append({'date': today, 'day': day_index, 'reward': reward['desc']})
        if len(checkin['history']) > 90:
            checkin['history'] = checkin['history'][-90:]
        reward_msg = reward['desc']
        add_gcoins(self.users, username, 10, 'checkin')
        self.save_users()
        self._check_and_unlock_achievements(username)
        return True, f'签到成功！获得 {reward_msg}', reward

    def get_daily_first_win_status(self, username):
        if username not in self.users:
            return None
        user_data = self.users[username]
        if 'daily_first_win' not in user_data:
            user_data['daily_first_win'] = {'last_date': '', 'claimed': False, 'total_claimed': 0}
            self.save_users()
        dfw = user_data['daily_first_win']
        today = self.get_today()
        if dfw.get('last_date') != today:
            dfw['claimed'] = False
            dfw['last_date'] = today
            self.save_users()
        return {'claimed': dfw.get('claimed', False), 'total_claimed': dfw.get('total_claimed', 0), 'reward': 5}

    def claim_daily_first_win(self, username):
        if username not in self.users:
            return False, '用户不存在'
        user_data = self.users[username]
        if 'daily_first_win' not in user_data:
            user_data['daily_first_win'] = {'last_date': '', 'claimed': False, 'total_claimed': 0}
        dfw = user_data['daily_first_win']
        today = self.get_today()
        if dfw.get('last_date') != today:
            dfw['claimed'] = False
            dfw['last_date'] = today
        if dfw.get('claimed', False):
            return False, '今日已领取首胜奖励'
        dfw['claimed'] = True
        dfw['total_claimed'] = dfw.get('total_claimed', 0) + 1
        dfw['last_date'] = today
        self.add_points(username, 5)
        add_gcoins(self.users, username, GCOIN_EARN_TABLE['daily_first_win'], 'daily_first_win')
        self.save_users()
        self._check_and_unlock_achievements(username)
        return True, f'领取成功！获得 5 积分 + {GCOIN_EARN_TABLE["daily_first_win"]} G币'

    def get_chest_status(self, username):
        if username not in self.users:
            return None
        user_data = self.users[username]
        if 'chests' not in user_data:
            user_data['chests'] = {'date': '', 'opened': [], 'streak_all_days': 0, 'last_full_open_date': ''}
            self.save_users()
        chests = user_data['chests']
        today = self.get_today()
        if chests.get('date') != today:
            if chests.get('date') and len(chests.get('opened', [])) >= len(CHEST_REWARDS):
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                if chests.get('date') == yesterday:
                    chests['streak_all_days'] = chests.get('streak_all_days', 0) + 1
                else:
                    chests['streak_all_days'] = 1
                chests['last_full_open_date'] = chests.get('date', '')
            else:
                if chests.get('date'):
                    chests['streak_all_days'] = 0
            chests['date'] = today
            chests['opened'] = []
            self.save_users()
        stats = self.get_user_game_stats(username)
        today_plays = stats.get('today_plays', 0)
        opened = chests.get('opened', [])
        result = []
        for c in CHEST_REWARDS:
            result.append({
                'plays': c['plays'],
                'name': c['name'],
                'icon': c['icon'],
                'points_min': c['points_min'],
                'points_max': c['points_max'],
                'item_chance': c.get('item_chance', 0),
                'gcoin_min': c.get('gcoin_min', 0),
                'gcoin_max': c.get('gcoin_max', 0),
                'unlocked': today_plays >= c['plays'],
                'opened': c['plays'] in opened
            })
        return {
            'today_plays': today_plays,
            'chests': result,
            'all_opened': len(opened) >= len(CHEST_REWARDS),
            'opened_count': len(opened),
            'total_count': len(CHEST_REWARDS),
            'streak_all_days': chests.get('streak_all_days', 0)
        }

    def open_chest(self, username, chest_plays):
        if username not in self.users:
            return False, '用户不存在', 0, None
        user_data = self.users[username]
        if 'chests' not in user_data:
            user_data['chests'] = {'date': '', 'opened': [], 'streak_all_days': 0}
        chests = user_data['chests']
        today = self.get_today()
        if chests.get('date') != today:
            chests['date'] = today
            chests['opened'] = []
        if chest_plays in chests.get('opened', []):
            return False, '该宝箱已开启', 0, None
        stats = self.get_user_game_stats(username)
        today_plays = stats.get('today_plays', 0)
        chest_info = None
        for c in CHEST_REWARDS:
            if c['plays'] == chest_plays:
                chest_info = c
                break
        if not chest_info:
            return False, '宝箱不存在', 0, None
        if today_plays < chest_info['plays']:
            return False, f'今日还需玩 {chest_info["plays"] - today_plays} 局才能解锁', 0, None
        points = random.randint(chest_info['points_min'], chest_info['points_max'])
        gcoins = 0
        if chest_info.get('gcoin_min', 0) > 0:
            gcoins = random.randint(chest_info['gcoin_min'], chest_info['gcoin_max'])
        chests.setdefault('opened', []).append(chest_plays)
        self.add_points(username, points)
        if gcoins > 0:
            add_gcoins(self.users, username, gcoins, 'chest_open')
        item_reward = None
        if chest_info.get('item_chance', 0) > 0 and random.random() < chest_info['item_chance']:
            basic_items = [i for i in ITEM_SHOP.values() if not i.get('member_only', False)]
            if basic_items:
                item_info = random.choice(basic_items)
                if 'items' not in user_data:
                    user_data['items'] = {}
                if item_info['id'] not in user_data['items']:
                    user_data['items'][item_info['id']] = {
                        'id': item_info['id'], 'name': item_info['name'],
                        'icon': item_info['icon'], 'desc': item_info['desc'],
                        'count': 0, 'expires_at': 0
                    }
                user_data['items'][item_info['id']]['count'] = user_data['items'][item_info['id']].get('count', 0) + 1
                item_reward = item_info['name']
        self.save_users()
        self._check_and_unlock_achievements(username)
        msg_parts = [f'获得 {points} 积分']
        if gcoins > 0:
            msg_parts.append(f'{gcoins} G币')
        if item_reward:
            msg_parts.append(f'{item_reward} x1')
        return True, f'开启{chest_info["name"]}，' + ' + '.join(msg_parts), points, item_reward

    def get_daily_bonus_status(self, username):
        if username not in self.users:
            return None
        user_data = self.users[username]
        if 'daily_bonus' not in user_data:
            user_data['daily_bonus'] = {'last_date': '', 'spins': 0, 'used_free': False}
            self.save_users()
        db = user_data['daily_bonus']
        today = self.get_today()
        if db.get('last_date') != today:
            db['last_date'] = today
            db['used_free'] = False
            db['spins'] = 0
            self.save_users()
        return {'used_free': db.get('used_free', False), 'can_spin': not db.get('used_free', False), 'spins': db.get('spins', 0)}

    def spin_daily_bonus(self, username):
        if username not in self.users:
            return False, '用户不存在', None
        user_data = self.users[username]
        if 'daily_bonus' not in user_data:
            user_data['daily_bonus'] = {'last_date': '', 'spins': 0, 'used_free': False}
        db = user_data['daily_bonus']
        today = self.get_today()
        if db.get('last_date') != today:
            db['last_date'] = today
            db['used_free'] = False
            db['spins'] = 0
        if db.get('used_free', False):
            return False, '今日免费抽奖已用完', None
        rewards = [
            {'icon': '💧', 'name': '1积分', 'points': 1, 'gcoins': 10, 'weight': 30},
            {'icon': '💧', 'name': '2积分', 'points': 2, 'gcoins': 20, 'weight': 25},
            {'icon': '💰', 'name': '3积分', 'points': 3, 'gcoins': 30, 'weight': 20},
            {'icon': '💰', 'name': '5积分', 'points': 5, 'gcoins': 50, 'weight': 15},
            {'icon': '💎', 'name': '8积分', 'points': 8, 'gcoins': 80, 'weight': 8},
            {'icon': '🌟', 'name': '15积分', 'points': 15, 'gcoins': 150, 'weight': 2}
        ]
        total_weight = sum(r['weight'] for r in rewards)
        rand = random.uniform(0, total_weight)
        cumulative = 0
        selected = rewards[-1]
        for r in rewards:
            cumulative += r['weight']
            if rand <= cumulative:
                selected = r
                break
        db['used_free'] = True
        db['spins'] = db.get('spins', 0) + 1
        self.add_points(username, selected['points'])
        add_gcoins(self.users, username, selected.get('gcoins', 0), 'daily_bonus')
        self.save_users()
        return True, f'恭喜获得 {selected["name"]} + {selected.get("gcoins", 0)} G币', selected

    def can_play(self, username):
        stats = self.get_user_game_stats(username)
        if not stats:
            return False
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        return stats.get('today_plays', 0) < max_plays

    def get_remaining_plays(self, username):
        stats = self.get_user_game_stats(username)
        if not stats:
            return 0
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        return max(0, max_plays - stats.get('today_plays', 0))

    def record_play(self, username, won, points_earned, game_id='', check_achievements=True, gcoins_earned=0):
        stats = self.get_user_game_stats(username)
        if not stats:
            return None
        stats['today_plays'] = stats.get('today_plays', 0) + 1
        stats['total_plays'] = stats.get('total_plays', 0) + 1
        if game_id:
            if 'game_plays' not in stats:
                stats['game_plays'] = {}
            stats['game_plays'][game_id] = stats['game_plays'].get(game_id, 0) + 1
        if won:
            stats['total_wins'] = stats.get('total_wins', 0) + 1
            stats['today_wins'] = stats.get('today_wins', 0) + 1
            if game_id:
                if 'game_wins' not in stats:
                    stats['game_wins'] = {}
                stats['game_wins'][game_id] = stats['game_wins'].get(game_id, 0) + 1
        if points_earned > 0:
            stats['total_points_earned'] = round(stats.get('total_points_earned', 0) + points_earned, 2)
            stats['today_points'] = round(stats.get('today_points', 0) + points_earned, 2)
        if gcoins_earned > 0:
            add_gcoins(self.users, username, gcoins_earned, f'game_win_{game_id}')
        self.save_users()
        if points_earned > 0 and won:
            self.add_points(username, points_earned)
        if check_achievements:
            self._check_and_unlock_achievements(username)
        return stats

    def calculate_points(self, won, game_type, extra_data=None):
        if not won:
            return 0
        base_ranges = {
            'dice': (5, 25), 'blackjack': (10, 50), 'guess_number': (8, 35),
            'rock_paper_scissors': (3, 15), 'roulette': (15, 100),
            'lucky_wheel': (10, 80), 'memory_cards': (10, 60), 'whack_mole': (8, 50),
            'dice_royale': (30, 120), 'blackjack_tournament': (50, 200),
            'treasure_hunt': (40, 180), 'boss_battle': (60, 300)
        }
        base_min, base_max = base_ranges.get(game_type, (5, 20))
        if game_type == 'dice' and extra_data:
            diff = extra_data.get('diff', 0)
            if diff <= 1:
                base_min, base_max = 20, 40
            elif diff <= 3:
                base_min, base_max = 10, 25
            elif diff <= 6:
                base_min, base_max = 5, 15
        elif game_type == 'blackjack' and extra_data:
            player_total = extra_data.get('player_total', 0)
            dealer_total = extra_data.get('dealer_total', 0)
            if player_total == 21 and dealer_total != 21:
                base_min, base_max = 30, 55
            elif player_total > dealer_total:
                base_min, base_max = 10, 35
            else:
                base_min, base_max = 5, 15
        elif game_type == 'guess_number' and extra_data:
            attempts = extra_data.get('attempts', 0)
            if attempts <= 3:
                base_min, base_max = 25, 45
            elif attempts <= 5:
                base_min, base_max = 15, 30
            else:
                base_min, base_max = 5, 15
        elif game_type == 'rock_paper_scissors' and extra_data:
            rounds = extra_data.get('rounds', 1)
            if rounds >= 3:
                base_min, base_max = 10, 25
            else:
                base_min, base_max = 3, 12
        elif game_type == 'roulette' and extra_data:
            multiplier = extra_data.get('multiplier', 1)
            if multiplier >= 35:
                base_min, base_max = 60, 100
            elif multiplier >= 10:
                base_min, base_max = 30, 60
            elif multiplier >= 5:
                base_min, base_max = 15, 35
            else:
                base_min, base_max = 8, 20
        elif game_type == 'lucky_wheel' and extra_data:
            multiplier = extra_data.get('multiplier', 1)
            if multiplier >= 10:
                base_min, base_max = 50, 80
            elif multiplier >= 5:
                base_min, base_max = 25, 50
            elif multiplier >= 2:
                base_min, base_max = 12, 30
            else:
                base_min, base_max = 5, 15
        elif game_type == 'memory_cards' and extra_data:
            moves = extra_data.get('moves', 99)
            if moves <= 12:
                base_min, base_max = 40, 60
            elif moves <= 18:
                base_min, base_max = 25, 40
            elif moves <= 24:
                base_min, base_max = 15, 25
            else:
                base_min, base_max = 8, 15
        elif game_type == 'whack_mole' and extra_data:
            score = extra_data.get('score', 0)
            if score >= 25:
                base_min, base_max = 25, 50
            elif score >= 15:
                base_min, base_max = 15, 35
            else:
                base_min, base_max = 8, 20
        elif game_type == 'dice_royale' and extra_data:
            score = extra_data.get('score', 0)
            if score >= 100:
                base_min, base_max = 80, 120
            elif score >= 60:
                base_min, base_max = 50, 80
            else:
                base_min, base_max = 30, 50
        elif game_type == 'blackjack_tournament' and extra_data:
            wins = extra_data.get('wins', 0)
            if wins >= 3:
                base_min, base_max = 150, 200
            elif wins >= 2:
                base_min, base_max = 80, 150
            else:
                base_min, base_max = 50, 80
        elif game_type == 'treasure_hunt' and extra_data:
            treasures = extra_data.get('treasures', 0)
            if treasures >= 5:
                base_min, base_max = 120, 180
            elif treasures >= 3:
                base_min, base_max = 70, 120
            else:
                base_min, base_max = 40, 70
        elif game_type == 'boss_battle' and extra_data:
            damage = extra_data.get('damage', 0)
            if damage >= 100:
                base_min, base_max = 200, 300
            elif damage >= 60:
                base_min, base_max = 120, 200
            else:
                base_min, base_max = 60, 120
        points = random.randint(base_min, base_max)
        if extra_data and extra_data.get('username'):
            username = extra_data.get('username')
            bonus_rate = get_member_bonus_rate(self.users, username)
            if bonus_rate > 0:
                points = int(round(points * (1 + bonus_rate)))
        return points

    def apply_streak_and_consolation(self, username, won, points, game_type, extra_data=None):
        streak = self.update_win_streak(username, won)
        final_points = points
        bonus_message = ''
        if won and streak.get('bonus_rate', 0) > 0:
            bonus_points = int(round(points * streak['bonus_rate']))
            final_points = points + bonus_points
            bonus_message = f'{streak["bonus_message"]}（+{bonus_points} G币）'
        if not won and streak.get('current_lose', 0) >= 3:
            consolation = 2
            final_points = consolation
            bonus_message = f'💪 连败{streak["current_lose"]}局，获得安慰奖励+{consolation} G币'
            won = True
        return final_points, bonus_message, streak

    def apply_active_items(self, username, won, points, game_id):
        effects = self.get_active_effects(username)
        extra_message = ''
        if 'triple_card' in effects and won:
            points = points * 3
            extra_message = '💎 积分三倍卡生效！G币 ×3'
            self.consume_effects(username, 'triple_card', persist=False)
        elif 'double_card' in effects and won:
            points = points * 2
            extra_message = '✨ 双倍卡生效！G币翻倍'
            self.consume_effects(username, 'double_card', persist=False)
        if 'lucky_charm' in effects and game_id in ITEM_SHOP['lucky_charm']['games']:
            self.consume_effects(username, 'lucky_charm', persist=False)
        if 'member_lucky_charm' in effects and game_id in ITEM_SHOP['member_lucky_charm']['games']:
            self.consume_effects(username, 'member_lucky_charm', persist=False)
        return points, extra_message

    def check_amulet(self, username, won):
        effects = self.get_active_effects(username)
        if not won and 'amulet' in effects:
            self.consume_effects(username, 'amulet', persist=False)
            return True
        return False

    def check_insurance(self, username, won, points_lost=0):
        effects = self.get_active_effects(username)
        if not won and 'insurance' in effects:
            self.consume_effects(username, 'insurance', persist=False)
            return True
        return False

    def check_reroll(self, username, game_id):
        effects = self.get_active_effects(username)
        if 'reroll' in effects and game_id in ITEM_SHOP['reroll']['games']:
            return True
        return False

    def consume_reroll(self, username):
        self.consume_effects(username, 'reroll', persist=False)

    def play_dice(self, username, bet_type='high', bet_value=7, reroll=False):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        if reroll:
            if not self.check_reroll(username, 'dice'):
                return {'success': False, 'error': '没有可用的重投卡'}
        player_dice = [random.randint(1, 6) for _ in range(3)]
        ai_dice = [random.randint(1, 6) for _ in range(3)]
        player_total = sum(player_dice)
        ai_total = sum(ai_dice)
        if bet_type == 'high':
            won = player_total > ai_total
        elif bet_type == 'low':
            won = player_total < ai_total
        elif bet_type == 'over':
            won = player_total > bet_value
        elif bet_type == 'under':
            won = player_total < bet_value
        elif bet_type == 'odd':
            won = player_total % 2 == 1
        elif bet_type == 'even':
            won = player_total % 2 == 0
        elif bet_type == 'triple':
            won = (player_dice[0] == player_dice[1] == player_dice[2])
        else:
            won = player_total > ai_total
        if reroll:
            self.consume_reroll(username)
        diff = abs(player_total - ai_total)
        is_triple = (player_dice[0] == player_dice[1] == player_dice[2])
        extra_data = {'diff': diff, 'username': username, 'triple': is_triple}
        points = self.calculate_points(won, 'dice', extra_data)
        if won and is_triple:
            points = int(points * 2)
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'dice', extra_data)
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'dice')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, 0, 'dice', check_achievements=False, gcoins_earned=final_points)
        self.add_game_history(username, 'dice', won, final_points, f'你{player_total} vs AI{ai_total}' + (' [豹子]' if is_triple else ''))
        self.update_daily_tasks(username, 'dice', won)
        drops = self.roll_all_drops(username, 'dice', won)
        remaining = self.get_remaining_plays(username)
        if amulet_used:
            remaining = remaining + 1
            bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        return {
            'success': True,
            'won': won,
            'player_dice': player_dice,
            'player_total': player_total,
            'ai_dice': ai_dice,
            'ai_total': ai_total,
            'points_earned': final_points,
            'remaining_plays': remaining,
            'max_plays': max_plays,
            'is_member': is_game_member(self.users, username),
            'message': '🎉 你赢了！' + (' 豹子翻倍！' if is_triple and won else '') if won else '😔 你输了！',
            'diff': diff,
            'is_triple': is_triple,
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
            'drops': drops
        }

    def play_blackjack(self, username, double=False, insurance=False):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        effects = self.get_active_effects(username)
        has_insurance = insurance and 'insurance' in effects
        deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        random.shuffle(deck)
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        def hand_total(hand):
            total = sum(hand)
            aces = hand.count(11)
            while total > 21 and aces > 0:
                total -= 10
                aces -= 1
            return total

        player_total = hand_total(player_hand)
        dealer_total = hand_total(dealer_hand)
        dealer_second_card = dealer_hand[1] if len(dealer_hand) > 1 else 0
        dealer_shows_ace = (dealer_second_card == 11)
        insurance_bet = False
        insurance_won = False
        if has_insurance and dealer_shows_ace:
            insurance_bet = True
        dealer_hit_count = 0
        while dealer_total < 17:
            dealer_hand.append(deck.pop())
            dealer_total = hand_total(dealer_hand)
            dealer_hit_count += 1
        if insurance_bet:
            if dealer_total == 21:
                insurance_won = True
                self.consume_effects(username, 'insurance', persist=False)
        if player_total > 21:
            won = False
        elif dealer_total > 21:
            won = True
        elif player_total > dealer_total:
            won = True
        else:
            won = False
        is_double = False
        if double:
            if self.check_reroll(username, 'blackjack'):
                self.consume_reroll(username)
                is_double = True
        points = self.calculate_points(won, 'blackjack', {'player_total': player_total, 'dealer_total': dealer_total, 'username': username})
        if won and is_double:
            points = points * 2
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'blackjack', {'player_total': player_total, 'dealer_total': dealer_total})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'blackjack')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, 0, 'blackjack', check_achievements=False, gcoins_earned=final_points)
        self.add_game_history(username, 'blackjack', won, final_points, f'你{player_total} vs 庄家{dealer_total}' + (' [双倍]' if is_double else '') + (' [保险]' if insurance_won else ''))
        self.update_daily_tasks(username, 'blackjack', won)
        drops = self.roll_all_drops(username, 'blackjack', won)
        remaining = self.get_remaining_plays(username)
        if amulet_used:
            remaining = remaining + 1
            bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        return {
            'success': True,
            'won': won,
            'player_hand': player_hand,
            'player_total': player_total,
            'dealer_hand': dealer_hand,
            'dealer_total': dealer_total,
            'dealer_hit_count': dealer_hit_count,
            'points_earned': final_points,
            'remaining_plays': remaining,
            'max_plays': max_plays,
            'is_member': is_game_member(self.users, username),
            'message': '🎉 你赢了！' + (' 双倍！' if is_double and won else '') + (' 保险理赔！' if insurance_won else '') if won else '😔 你输了！',
            'is_double': is_double,
            'insurance_bet': insurance_bet,
            'insurance_won': insurance_won,
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
            'drops': drops
        }

    def start_guess_game(self, username, difficulty='normal'):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        if difficulty == 'easy':
            secret = random.randint(1, 50)
            max_attempts = 7
        elif difficulty == 'hard':
            secret = random.randint(1, 200)
            max_attempts = 8
        else:
            secret = random.randint(1, 100)
            max_attempts = 7
        self.guess_game_state[username] = {
            'secret': secret,
            'attempts': 0,
            'max_attempts': max_attempts,
            'hints': [],
            'active': True,
            'game_started': True,
            'difficulty': difficulty,
            'range_min': 1,
            'range_max': 50 if difficulty == 'easy' else (200 if difficulty == 'hard' else 100),
            'started_at': int(time.time() * 1000)
        }
        if username in self.users:
            self.users[username]['guess_state'] = self.guess_game_state[username]
            self.save_users()
        return {
            'success': True,
            'max_attempts': max_attempts,
            'difficulty': difficulty,
            'range_min': 1,
            'range_max': self.guess_game_state[username]['range_max'],
            'message': f'🎯 游戏已开始！{self.guess_game_state[username]["range_min"]}-{self.guess_game_state[username]["range_max"]}之间猜一个数字，你有{max_attempts}次机会'
        }

    def guess_number(self, username, guess):
        if username not in self.guess_game_state:
            if username in self.users and 'guess_state' in self.users[username]:
                self.guess_game_state[username] = self.users[username]['guess_state']
        if username not in self.guess_game_state:
            return {'success': False, 'error': '请先开始新游戏'}
        state = self.guess_game_state[username]
        if not state.get('active', False):
            return {'success': False, 'error': '游戏已结束，请重新开始'}
        if state['attempts'] >= state['max_attempts']:
            state['active'] = False
            return {'success': False, 'error': '已用尽所有机会，请重新开始'}
        range_max = state.get('range_max', 100)
        if guess < 1 or guess > range_max:
            return {'success': False, 'error': f'请输入1-{range_max}之间的数字'}
        state['attempts'] += 1
        secret = state['secret']
        if guess == secret:
            points = self.calculate_points(True, 'guess_number', {'attempts': state['attempts'], 'username': username})
            if state.get('difficulty') == 'hard':
                points = int(points * 1.5)
            final_points, bonus_message, streak = self.apply_streak_and_consolation(username, True, points, 'guess_number', {'attempts': state['attempts']})
            final_points, item_message = self.apply_active_items(username, True, final_points, 'guess_number')
            self.record_play(username, True, 0, 'guess_number', check_achievements=False, gcoins_earned=final_points)
            self.add_game_history(username, 'guess_number', True, final_points, f'{state["attempts"]}次猜中' + (' [困难]' if state.get('difficulty') == 'hard' else ''))
            self.update_daily_tasks(username, 'guess_number', True, {'attempts': state['attempts']})
            drops = self.roll_all_drops(username, 'guess_number', True)
            remaining = self.get_remaining_plays(username)
            user_data = self.users.get(username, {})
            bonus_plays = user_data.get('bonus_plays', 0)
            max_plays = get_member_max_plays(self.users, username) + bonus_plays
            state['active'] = False
            if username in self.users:
                self.users[username]['guess_state'] = state
                self.save_users()
            return {
                'success': True,
                'won': True,
                'secret': secret,
                'attempts': state['attempts'],
                'max_attempts': state['max_attempts'],
                'points_earned': final_points,
                'remaining_plays': remaining,
                'max_plays': max_plays,
                'is_member': is_game_member(self.users, username),
                'game_over': True,
                'message': '🎉 你猜对了！数字是 ' + str(secret) + '，用了 ' + str(state['attempts']) + ' 次！',
                'win_streak': streak.get('current_win', 0),
                'lose_streak': streak.get('current_lose', 0),
                'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
                'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
                'drops': drops
            }
        elif guess < secret:
            state['hints'].append(str(guess) + ' 太小了')
            hint = '📈 太小了，再大一点'
        else:
            state['hints'].append(str(guess) + ' 太大了')
            hint = '📉 太大了，再小一点'
        remaining_attempts = state['max_attempts'] - state['attempts']
        if remaining_attempts <= 0:
            state['active'] = False
            final_points, bonus_message, streak = self.apply_streak_and_consolation(username, False, 0, 'guess_number', {})
            amulet_used = self.check_amulet(username, False)
            self.record_play(username, False, 0, 'guess_number', check_achievements=False, gcoins_earned=final_points)
            self.add_game_history(username, 'guess_number', False, final_points, f'未猜中，答案{secret}')
            self.update_daily_tasks(username, 'guess_number', False)
            remaining = self.get_remaining_plays(username)
            if amulet_used:
                remaining = remaining + 1
                bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
            user_data = self.users.get(username, {})
            bonus_plays = user_data.get('bonus_plays', 0)
            max_plays = get_member_max_plays(self.users, username) + bonus_plays
            if username in self.users:
                self.users[username]['guess_state'] = state
                self.save_users()
            return {
                'success': True,
                'won': False,
                'game_over': True,
                'secret': secret,
                'attempts': state['attempts'],
                'max_attempts': state['max_attempts'],
                'points_earned': final_points,
                'remaining_plays': remaining,
                'max_plays': max_plays,
                'is_member': is_game_member(self.users, username),
                'message': '😔 你输了！数字是 ' + str(secret) + '，已用尽所有机会',
                'bonus_message': bonus_message,
                'card_drop': None,
                'drops': []
            }
        if username in self.users:
            self.users[username]['guess_state'] = state
            self.save_users()
        return {
            'success': True,
            'won': False,
            'hint': hint,
            'attempts': state['attempts'],
            'max_attempts': state['max_attempts'],
            'remaining_attempts': remaining_attempts,
            'game_over': False,
            'message': '❌ 猜错了！' + hint
        }

    def get_guess_game_state(self, username):
        if username in self.guess_game_state:
            return self.guess_game_state[username]
        if username in self.users and 'guess_state' in self.users[username]:
            state = self.users[username]['guess_state']
            if state.get('active', False):
                self.guess_game_state[username] = state
                return state
        return None

    def play_guess_number(self, username, guess=None, difficulty='normal'):
        if guess is None:
            return self.start_guess_game(username, difficulty)
        return self.guess_number(username, guess)

    def reset_guess_game(self, username):
        if username in self.guess_game_state:
            del self.guess_game_state[username]
        if username in self.users and 'guess_state' in self.users[username]:
            del self.users[username]['guess_state']
            self.save_users()
        return {'success': True, 'message': '游戏已重置'}

    def start_rps_game(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        self.rps_game_state[username] = {
            'player_wins': 0, 'ai_wins': 0, 'rounds_played': 0,
            'round_history': [], 'active': True, 'best_of': 3,
            'game_started': True, 'started_at': int(time.time() * 1000)
        }
        if username in self.users:
            self.users[username]['rps_state'] = self.rps_game_state[username]
            self.save_users()
        return {'success': True, 'waiting': True, 'message': '🤖 游戏已开始！请选择出拳：🪨 石头 | 📄 布 | ✂️ 剪刀'}

    def rps_choice(self, username, player_move):
        if username not in self.rps_game_state:
            if username in self.users and 'rps_state' in self.users[username]:
                self.rps_game_state[username] = self.users[username]['rps_state']
        if username not in self.rps_game_state:
            return {'success': False, 'error': '请先开始新游戏'}
        state = self.rps_game_state[username]
        if not state.get('active', False):
            return {'success': False, 'error': '游戏已结束，请重新开始'}
        moves = ['rock', 'paper', 'scissors']
        emojis = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}
        names = {'rock': '石头', 'paper': '布', 'scissors': '剪刀'}
        if player_move not in moves:
            return {'success': False, 'error': '无效的出拳，请选择 rock/paper/scissors'}
        if state['rounds_played'] >= 10:
            state['active'] = False
            return {'success': False, 'error': '游戏轮次过多，请重新开始'}
        state['rounds_played'] += 1
        ai_move = random.choice(moves)
        if player_move == ai_move:
            result = 'tie'
            round_result = '平局'
        elif (player_move == 'rock' and ai_move == 'scissors') or \
             (player_move == 'paper' and ai_move == 'rock') or \
             (player_move == 'scissors' and ai_move == 'paper'):
            result = 'win'
            round_result = '赢'
            state['player_wins'] += 1
        else:
            result = 'lose'
            round_result = '输'
            state['ai_wins'] += 1
        state['round_history'].append({
            'round': state['rounds_played'],
            'player_move': player_move,
            'player_emoji': emojis[player_move],
            'player_name': names[player_move],
            'ai_move': ai_move,
            'ai_emoji': emojis[ai_move],
            'ai_name': names[ai_move],
            'result': result,
            'round_result': round_result
        })
        if state['player_wins'] >= state['best_of'] or state['ai_wins'] >= state['best_of']:
            won = state['player_wins'] > state['ai_wins']
            points = self.calculate_points(won, 'rock_paper_scissors', {'rounds': state['rounds_played'], 'username': username})
            final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'rock_paper_scissors', {'rounds': state['rounds_played']})
            if bonus_message and not won:
                won = True
            final_points, item_message = self.apply_active_items(username, won, final_points, 'rock_paper_scissors')
            amulet_used = self.check_amulet(username, won)
            self.record_play(username, won, 0, 'rock_paper_scissors', check_achievements=False, gcoins_earned=final_points)
            self.add_game_history(username, 'rock_paper_scissors', won, final_points, f'比分 {state["player_wins"]}:{state["ai_wins"]}')
            self.update_daily_tasks(username, 'rock_paper_scissors', won)
            drops = self.roll_all_drops(username, 'rock_paper_scissors', won)
            remaining = self.get_remaining_plays(username)
            if amulet_used:
                remaining = remaining + 1
                bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
            user_data = self.users.get(username, {})
            bonus_plays = user_data.get('bonus_plays', 0)
            max_plays = get_member_max_plays(self.users, username) + bonus_plays
            state['active'] = False
            if username in self.users:
                self.users[username]['rps_state'] = state
                self.save_users()
            return {
                'success': True,
                'won': won,
                'player_wins': state['player_wins'],
                'ai_wins': state['ai_wins'],
                'rounds_played': state['rounds_played'],
                'round_history': state['round_history'],
                'best_of': state['best_of'],
                'points_earned': final_points,
                'remaining_plays': remaining,
                'max_plays': max_plays,
                'is_member': is_game_member(self.users, username),
                'game_over': True,
                'message': '🎉 你赢了！' if won else '😔 你输了！',
                'win_streak': streak.get('current_win', 0),
                'lose_streak': streak.get('current_lose', 0),
                'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
                'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
                'drops': drops
            }
        if username in self.users:
            self.users[username]['rps_state'] = state
            self.save_users()
        return {
            'success': True,
            'won': False,
            'player_move': player_move,
            'player_emoji': emojis[player_move],
            'player_name': names[player_move],
            'ai_move': ai_move,
            'ai_emoji': emojis[ai_move],
            'ai_name': names[ai_move],
            'result': result,
            'round_result': round_result,
            'player_wins': state['player_wins'],
            'ai_wins': state['ai_wins'],
            'rounds_played': state['rounds_played'],
            'best_of': state['best_of'],
            'game_over': False,
            'message': '第 ' + str(state['rounds_played']) + ' 轮：你 ' + round_result + '了！当前比分 ' + str(state['player_wins']) + ':' + str(state['ai_wins'])
        }

    def play_rps(self, username, player_move=None):
        if player_move is None:
            return self.start_rps_game(username)
        return self.rps_choice(username, player_move)

    def reset_rps(self, username):
        if username in self.rps_game_state:
            del self.rps_game_state[username]
        if username in self.users and 'rps_state' in self.users[username]:
            del self.users[username]['rps_state']
            self.save_users()
        return {'success': True, 'message': '游戏已重置'}

    def get_rps_game_state(self, username):
        if username in self.rps_game_state:
            return self.rps_game_state[username]
        if username in self.users and 'rps_state' in self.users[username]:
            state = self.users[username]['rps_state']
            if state.get('active', False):
                self.rps_game_state[username] = state
                return state
        return None

    def play_roulette(self, username, bet_type='number', bet_value=0, bet_combo=None):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        numbers = list(range(0, 37))
        red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
        black_numbers = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
        result = random.choice(numbers)
        multiplier = 1
        won = False
        win_desc = ''
        is_combo = False
        if bet_type == 'number':
            if bet_value in numbers and result == bet_value:
                won = True
                multiplier = 36
                win_desc = '数字 ' + str(bet_value) + ' 精确命中！'
                stats = self.get_user_game_stats(username)
                stats['roulette_number_hits'] = stats.get('roulette_number_hits', 0) + 1
                self.save_users()
        elif bet_type == 'red':
            if result in red_numbers:
                won = True
                multiplier = 2
                win_desc = '红色命中！'
        elif bet_type == 'black':
            if result in black_numbers:
                won = True
                multiplier = 2
                win_desc = '黑色命中！'
        elif bet_type == 'even':
            if result != 0 and result % 2 == 0:
                won = True
                multiplier = 2
                win_desc = '偶数命中！'
        elif bet_type == 'odd':
            if result != 0 and result % 2 == 1:
                won = True
                multiplier = 2
                win_desc = '奇数命中！'
        elif bet_type == 'high':
            if result >= 19 and result <= 36:
                won = True
                multiplier = 2
                win_desc = '大数（19-36）命中！'
        elif bet_type == 'low':
            if result >= 1 and result <= 18:
                won = True
                multiplier = 2
                win_desc = '小数（1-18）命中！'
        elif bet_type == 'combo' and bet_combo:
            is_combo = True
            combo_type = bet_combo.get('type', '')
            combo_value = bet_combo.get('value', '')
            combo_matched = False
            if combo_type == 'red_high':
                combo_matched = (result in red_numbers) and (19 <= result <= 36)
                win_desc = '红+大 组合命中！'
            elif combo_type == 'red_low':
                combo_matched = (result in red_numbers) and (1 <= result <= 18)
                win_desc = '红+小 组合命中！'
            elif combo_type == 'black_high':
                combo_matched = (result in black_numbers) and (19 <= result <= 36)
                win_desc = '黑+大 组合命中！'
            elif combo_type == 'black_low':
                combo_matched = (result in black_numbers) and (1 <= result <= 18)
                win_desc = '黑+小 组合命中！'
            elif combo_type == 'red_even':
                combo_matched = (result in red_numbers) and (result != 0 and result % 2 == 0)
                win_desc = '红+偶 组合命中！'
            elif combo_type == 'red_odd':
                combo_matched = (result in red_numbers) and (result != 0 and result % 2 == 1)
                win_desc = '红+奇 组合命中！'
            elif combo_type == 'black_even':
                combo_matched = (result in black_numbers) and (result != 0 and result % 2 == 0)
                win_desc = '黑+偶 组合命中！'
            elif combo_type == 'black_odd':
                combo_matched = (result in black_numbers) and (result != 0 and result % 2 == 1)
                win_desc = '黑+奇 组合命中！'
            if combo_matched:
                won = True
                multiplier = 4
        else:
            if result != 0:
                won = True
                multiplier = 2
                win_desc = '非零命中！'
        color = ''
        if result == 0:
            color = '🟢 绿色'
        elif result in red_numbers:
            color = '🔴 红色'
        else:
            color = '⚫ 黑色'
        points = self.calculate_points(won, 'roulette', {'multiplier': multiplier, 'username': username})
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'roulette', {'multiplier': multiplier})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'roulette')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, 0, 'roulette', check_achievements=False, gcoins_earned=final_points)
        self.add_game_history(username, 'roulette', won, final_points, f'结果{result} {color} 下注{bet_type}')
        self.update_daily_tasks(username, 'roulette', won)
        drops = self.roll_all_drops(username, 'roulette', won)
        remaining = self.get_remaining_plays(username)
        if amulet_used:
            remaining = remaining + 1
            bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        return {
            'success': True,
            'won': won,
            'result': result,
            'color': color,
            'bet_type': bet_type,
            'bet_value': bet_value,
            'bet_combo': bet_combo,
            'multiplier': multiplier,
            'win_desc': win_desc,
            'is_combo': is_combo,
            'points_earned': final_points,
            'remaining_plays': remaining,
            'max_plays': max_plays,
            'is_member': is_game_member(self.users, username),
            'message': '🎉 你赢了！' + (win_desc if win_desc else '') if won else '😔 你输了！',
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
            'drops': drops
        }

    def get_lucky_wheel_segments(self):
        return [
            {'label': '谢谢参与', 'multiplier': 0, 'weight': 25, 'color': '#4b5563'},
            {'label': 'x1', 'multiplier': 1, 'weight': 25, 'color': '#6b7280'},
            {'label': 'x2', 'multiplier': 2, 'weight': 20, 'color': '#10b981'},
            {'label': 'x3', 'multiplier': 3, 'weight': 12, 'color': '#3b82f6'},
            {'label': 'x5', 'multiplier': 5, 'weight': 8, 'color': '#8b5cf6'},
            {'label': 'x8', 'multiplier': 8, 'weight': 5, 'color': '#f59e0b'},
            {'label': 'x10', 'multiplier': 10, 'weight': 3, 'color': '#ef4444'},
            {'label': 'x20', 'multiplier': 20, 'weight': 2, 'color': '#ec4899'}
        ]

    def play_lucky_wheel(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        tier = get_member_tier(self.users, username)
        base_tier = _get_base_tier(tier)
        if base_tier not in ['gold', 'diamond', 'supreme']:
            return {'success': False, 'error': '幸运转盘是黄金会员及以上专属游戏'}
        segments = self.get_lucky_wheel_segments()
        total_weight = sum(s['weight'] for s in segments)
        rand = random.uniform(0, total_weight)
        cumulative = 0
        selected_index = 0
        for i, seg in enumerate(segments):
            cumulative += seg['weight']
            if rand <= cumulative:
                selected_index = i
                break
        selected = segments[selected_index]
        won = selected['multiplier'] > 0
        points = 0
        if won:
            points = self.calculate_points(True, 'lucky_wheel', {'multiplier': selected['multiplier'], 'username': username})
        if selected['multiplier'] >= 20:
            stats = self.get_user_game_stats(username)
            stats['lucky_x20'] = stats.get('lucky_x20', 0) + 1
            self.save_users()
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'lucky_wheel', {'multiplier': selected['multiplier']})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'lucky_wheel')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, 0, 'lucky_wheel', check_achievements=False, gcoins_earned=final_points)
        self.add_game_history(username, 'lucky_wheel', won, final_points, f'转盘结果 {selected["label"]}')
        self.update_daily_tasks(username, 'lucky_wheel', won)
        drops = self.roll_all_drops(username, 'lucky_wheel', won)
        remaining = self.get_remaining_plays(username)
        if amulet_used:
            remaining = remaining + 1
            bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        return {
            'success': True,
            'won': won,
            'selected_index': selected_index,
            'label': selected['label'],
            'multiplier': selected['multiplier'],
            'segments': [{'label': s['label'], 'color': s['color'], 'multiplier': s['multiplier']} for s in segments],
            'points_earned': final_points,
            'remaining_plays': remaining,
            'max_plays': max_plays,
            'is_member': is_game_member(self.users, username),
            'message': f'🎉 恭喜获得 {selected["label"]}！' if won else '😔 谢谢参与！',
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
            'drops': drops
        }

    def start_memory_game(self, username, difficulty='normal'):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        tier = get_member_tier(self.users, username)
        base_tier = _get_base_tier(tier)
        if base_tier not in ['diamond', 'supreme']:
            return {'success': False, 'error': '记忆翻牌是钻石会员及以上专属游戏'}
        if difficulty == 'hard':
            symbols = ['🍎', '🍌', '🍇', '🍓', '🍒', '🍑', '🥝', '🍍', '🍉', '🍊', '🍋', '🍈', '🫐', '🍅', '🥭', '🍍']
            cards = symbols[:12] + symbols[:12]
            grid_size = 24
            total_pairs = 12
        else:
            symbols = ['🍎', '🍌', '🍇', '🍓', '🍒', '🍑', '🥝', '🍍']
            cards = symbols + symbols
            grid_size = 16
            total_pairs = 8
        random.shuffle(cards)
        self.memory_game_state[username] = {
            'cards': cards,
            'flipped': [],
            'matched': [],
            'moves': 0,
            'active': True,
            'difficulty': difficulty,
            'grid_size': grid_size,
            'total_pairs': total_pairs,
            'started_at': int(time.time() * 1000)
        }
        if username in self.users:
            self.users[username]['memory_state'] = self.memory_game_state[username]
            self.save_users()
        return {
            'success': True,
            'cards': cards,
            'total_pairs': total_pairs,
            'grid_size': grid_size,
            'difficulty': difficulty,
            'message': '🃏 游戏开始！翻开两张相同的牌即可配对' + ('（困难模式：24张）' if difficulty == 'hard' else '')
        }

    def flip_memory_card(self, username, index):
        if username not in self.memory_game_state:
            if username in self.users and 'memory_state' in self.users[username]:
                self.memory_game_state[username] = self.users[username]['memory_state']
        if username not in self.memory_game_state:
            return {'success': False, 'error': '请先开始新游戏'}
        state = self.memory_game_state[username]
        if not state.get('active', False):
            return {'success': False, 'error': '游戏已结束，请重新开始'}
        grid_size = state.get('grid_size', 16)
        if index < 0 or index >= grid_size:
            return {'success': False, 'error': '无效的卡片位置'}
        if index in state['flipped'] or index in state['matched']:
            return {'success': False, 'error': '该卡片已翻开'}
        if len(state['flipped']) >= 2:
            state['flipped'] = []
        state['flipped'].append(index)
        is_match = False
        game_over = False
        final_points = 0
        bonus_message = ''
        streak = {'current_win': 0, 'current_lose': 0}
        drops = []
        if len(state['flipped']) == 2:
            state['moves'] += 1
            i1, i2 = state['flipped']
            if state['cards'][i1] == state['cards'][i2]:
                state['matched'].extend([i1, i2])
                state['flipped'] = []
                is_match = True
                if len(state['matched']) == grid_size:
                    state['active'] = False
                    game_over = True
                    points = self.calculate_points(True, 'memory_cards', {'moves': state['moves'], 'username': username})
                    if state.get('difficulty') == 'hard':
                        points = int(points * 1.8)
                    if state['moves'] <= (15 if state.get('difficulty') != 'hard' else 22):
                        stats = self.get_user_game_stats(username)
                        stats['memory_perfect'] = stats.get('memory_perfect', 0) + 1
                        self.save_users()
                    final_points, bonus_message, streak = self.apply_streak_and_consolation(username, True, points, 'memory_cards', {'moves': state['moves']})
                    final_points, item_message = self.apply_active_items(username, True, final_points, 'memory_cards')
                    if item_message:
                        bonus_message = (bonus_message + ' ' if bonus_message else '') + item_message
                    self.record_play(username, True, 0, 'memory_cards', check_achievements=False, gcoins_earned=final_points)
                    self.add_game_history(username, 'memory_cards', True, final_points, f'{state["moves"]}步完成' + (' [困难]' if state.get('difficulty') == 'hard' else ''))
                    self.update_daily_tasks(username, 'memory_cards', True)
                    drops = self.roll_all_drops(username, 'memory_cards', True)
        if username in self.users:
            self.users[username]['memory_state'] = state
            self.save_users()
        if game_over:
            remaining = self.get_remaining_plays(username)
            user_data = self.users.get(username, {})
            bonus_plays = user_data.get('bonus_plays', 0)
            max_plays = get_member_max_plays(self.users, username) + bonus_plays
            return {
                'success': True,
                'index': index,
                'is_match': True,
                'game_over': True,
                'won': True,
                'moves': state['moves'],
                'matched': state['matched'],
                'flipped': state['flipped'],
                'points_earned': final_points,
                'remaining_plays': remaining,
                'max_plays': max_plays,
                'message': f'🎉 全部配对成功！用了{state["moves"]}步，获得{final_points}G币',
                'win_streak': streak.get('current_win', 0),
                'lose_streak': streak.get('current_lose', 0),
                'bonus_message': bonus_message,
                'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
                'drops': drops
            }
        return {
            'success': True,
            'index': index,
            'is_match': is_match,
            'game_over': False,
            'moves': state['moves'],
            'flipped': state['flipped'],
            'matched': state['matched'],
            'pair_complete': len(state['flipped']) == 2 and not is_match
        }

    def reset_memory_game(self, username):
        if username in self.memory_game_state:
            del self.memory_game_state[username]
        if username in self.users and 'memory_state' in self.users[username]:
            del self.users[username]['memory_state']
            self.save_users()
        return {'success': True, 'message': '游戏已重置'}

    def play_memory_cards(self, username, action=None, index=None, difficulty='normal'):
        if action == 'start' or action is None:
            return self.start_memory_game(username, difficulty)
        if action == 'flip':
            return self.flip_memory_card(username, index)
        return {'success': False, 'error': '无效的操作'}

    def get_memory_game_state(self, username):
        if username in self.memory_game_state:
            return self.memory_game_state[username]
        if username in self.users and 'memory_state' in self.users[username]:
            state = self.users[username]['memory_state']
            if state.get('active', False):
                self.memory_game_state[username] = state
                return state
        return None

    def start_whack_game(self, username, difficulty='normal'):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        effects = self.get_active_effects(username)
        has_scope = 'scope' in effects
        if has_scope:
            self.consume_effects(username, 'scope', persist=False)
        if difficulty == 'hard':
            duration = 30
            spawn_interval_min = 250
            spawn_interval_max = 450
        elif difficulty == 'easy':
            duration = 45
            spawn_interval_min = 600
            spawn_interval_max = 900
        else:
            duration = 30
            spawn_interval_min = 400
            spawn_interval_max = 700
        if has_scope:
            duration += 10
        self.whack_game_state[username] = {
            'score': 0, 'hits': 0, 'bombs': 0, 'active': True,
            'duration': duration, 'difficulty': difficulty,
            'spawn_interval_min': spawn_interval_min,
            'spawn_interval_max': spawn_interval_max,
            'started_at': int(time.time() * 1000),
            'has_scope': has_scope
        }
        if username in self.users:
            self.users[username]['whack_state'] = self.whack_game_state[username]
            self.save_users()
        return {
            'success': True,
            'duration': duration,
            'difficulty': difficulty,
            'spawn_interval_min': spawn_interval_min,
            'spawn_interval_max': spawn_interval_max,
            'has_scope': has_scope,
            'message': f'🔨 游戏开始！{duration}秒内点击地鼠，避开炸弹' + ('（瞄准镜已生效：+10秒）' if has_scope else '')
        }

    def whack_hit(self, username, score, hits, bombs):
        if username not in self.whack_game_state:
            if username in self.users and 'whack_state' in self.users[username]:
                self.whack_game_state[username] = self.users[username]['whack_state']
        if username not in self.whack_game_state:
            return {'success': False, 'error': '请先开始新游戏'}
        state = self.whack_game_state[username]
        if not state.get('active', False):
            return {'success': False, 'error': '游戏已结束，请重新开始'}
        state['score'] = score
        state['hits'] = hits
        state['bombs'] = bombs
        if username in self.users:
            self.users[username]['whack_state'] = state
            self.save_users()
        return {'success': True, 'score': score, 'hits': hits, 'bombs': bombs, 'active': True}

    def finish_whack_game(self, username, score, hits, bombs):
        if username not in self.whack_game_state:
            if username in self.users and 'whack_state' in self.users[username]:
                self.whack_game_state[username] = self.users[username]['whack_state']
        if username not in self.whack_game_state:
            return {'success': False, 'error': '请先开始新游戏'}
        state = self.whack_game_state[username]
        if not state.get('active', False):
            return {'success': False, 'error': '游戏已结束'}
        state['active'] = False
        state['score'] = score
        state['hits'] = hits
        state['bombs'] = bombs
        final_score = max(0, score)
        won = final_score > 0
        points = 0
        if won:
            points = self.calculate_points(True, 'whack_mole', {'score': final_score, 'username': username})
            if state.get('difficulty') == 'hard':
                points = int(points * 1.4)
        if final_score >= 30:
            stats = self.get_user_game_stats(username)
            stats['whack_score_30'] = stats.get('whack_score_30', 0) + 1
            self.save_users()
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'whack_mole', {'score': final_score})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'whack_mole')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, 0, 'whack_mole', check_achievements=False, gcoins_earned=final_points)
        self.add_game_history(username, 'whack_mole', won, final_points, f'得分{final_score} 打中{hits} 炸弹{bombs}' + (' [困难]' if state.get('difficulty') == 'hard' else ''))
        self.update_daily_tasks(username, 'whack_mole', won)
        drops = self.roll_all_drops(username, 'whack_mole', won)
        remaining = self.get_remaining_plays(username)
        if amulet_used:
            remaining = remaining + 1
            bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        if username in self.users:
            self.users[username]['whack_state'] = state
            self.save_users()
        return {
            'success': True,
            'won': won,
            'score': final_score,
            'hits': hits,
            'bombs': bombs,
            'points_earned': final_points,
            'remaining_plays': remaining,
            'max_plays': max_plays,
            'message': f'🎉 得分 {final_score}！' if won else '😔 得分 0，未获得G币',
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
            'drops': drops
        }

    def play_whack_mole(self, username, action=None, score=0, hits=0, bombs=0, difficulty='normal'):
        if action == 'start' or action is None:
            return self.start_whack_game(username, difficulty)
        if action == 'hit':
            return self.whack_hit(username, score, hits, bombs)
        if action == 'finish':
            return self.finish_whack_game(username, score, hits, bombs)
        return {'success': False, 'error': '无效的操作'}

    def play_dice_royale(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        tier = get_member_tier(self.users, username)
        base_tier = _get_base_tier(tier)
        if base_tier not in ['gold', 'diamond', 'supreme']:
            return {'success': False, 'error': '骰子王者是黄金会员及以上专属游戏'}
        player_dice = [random.randint(1, 6) for _ in range(5)]
        ai_dice = [random.randint(1, 6) for _ in range(5)]
        player_dice.sort(reverse=True)
        ai_dice.sort(reverse=True)
        score_map = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60}
        player_score = sum(score_map[d] for d in player_dice)
        ai_score = sum(score_map[d] for d in ai_dice)
        won = player_score > ai_score
        is_royal = player_dice.count(player_dice[0]) >= 3
        points = self.calculate_points(won, 'dice_royale', {'score': player_score, 'username': username})
        if won and is_royal:
            points = int(points * 2)
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'dice_royale', {'score': player_score})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'dice_royale')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, 0, 'dice_royale', check_achievements=False, gcoins_earned=final_points)
        self.add_game_history(username, 'dice_royale', won, final_points, f'你{player_score}分 vs AI{ai_score}分' + (' [皇家骰]' if is_royal else ''))
        self.update_daily_tasks(username, 'dice_royale', won)
        drops = self.roll_all_drops(username, 'dice_royale', won)
        remaining = self.get_remaining_plays(username)
        if amulet_used:
            remaining = remaining + 1
            bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        return {
            'success': True,
            'won': won,
            'player_dice': player_dice,
            'ai_dice': ai_dice,
            'player_score': player_score,
            'ai_score': ai_score,
            'is_royal': is_royal,
            'points_earned': final_points,
            'remaining_plays': remaining,
            'max_plays': max_plays,
            'is_member': is_game_member(self.users, username),
            'message': '🎉 你赢了！' + (' 皇家骰翻倍！' if is_royal and won else '') if won else '😔 你输了！',
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
            'drops': drops
        }

    def play_blackjack_tournament(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        tier = get_member_tier(self.users, username)
        base_tier = _get_base_tier(tier)
        if base_tier not in ['diamond', 'supreme']:
            return {'success': False, 'error': '21点锦标赛是钻石会员及以上专属游戏'}

        def play_one_round():
            deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
            random.shuffle(deck)
            player_hand = [deck.pop(), deck.pop()]
            dealer_hand = [deck.pop(), deck.pop()]

            def hand_total(hand):
                total = sum(hand)
                aces = hand.count(11)
                while total > 21 and aces > 0:
                    total -= 10
                    aces -= 1
                return total

            player_total = hand_total(player_hand)
            dealer_total = hand_total(dealer_hand)
            while dealer_total < 17:
                dealer_hand.append(deck.pop())
                dealer_total = hand_total(dealer_hand)
            if player_total > 21:
                return False, player_total, dealer_total
            if dealer_total > 21:
                return True, player_total, dealer_total
            return player_total > dealer_total, player_total, dealer_total

        wins = 0
        rounds_detail = []
        for r in range(3):
            round_won, p_total, d_total = play_one_round()
            rounds_detail.append({'round': r + 1, 'won': round_won, 'player': p_total, 'dealer': d_total})
            if round_won:
                wins += 1
        won_all = wins == 3
        won = wins >= 2
        points = self.calculate_points(won, 'blackjack_tournament', {'wins': wins, 'username': username})
        if won_all:
            points = int(points * 2)
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'blackjack_tournament', {'wins': wins})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'blackjack_tournament')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, 0, 'blackjack_tournament', check_achievements=False, gcoins_earned=final_points)
        self.add_game_history(username, 'blackjack_tournament', won, final_points, f'胜{wins}/3局' + (' [全胜]' if won_all else ''))
        self.update_daily_tasks(username, 'blackjack_tournament', won)
        drops = self.roll_all_drops(username, 'blackjack_tournament', won)
        remaining = self.get_remaining_plays(username)
        if amulet_used:
            remaining = remaining + 1
            bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        return {
            'success': True,
            'won': won,
            'wins': wins,
            'won_all': won_all,
            'rounds_detail': rounds_detail,
            'points_earned': final_points,
            'remaining_plays': remaining,
            'max_plays': max_plays,
            'is_member': is_game_member(self.users, username),
            'message': '🎉 锦标赛胜利！' + (' 全胜翻倍！' if won_all else '') if won else '😔 锦标赛失败！',
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
            'drops': drops
        }

    def play_treasure_hunt(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        tier = get_member_tier(self.users, username)
        base_tier = _get_base_tier(tier)
        if base_tier not in ['supreme']:
            return {'success': False, 'error': '寻宝迷宫是至尊会员专属游戏'}
        grid = []
        treasures = 0
        bombs = 0
        for i in range(9):
            r = random.random()
            if r < 0.4:
                grid.append('treasure')
                treasures += 1
            elif r < 0.6:
                grid.append('bomb')
                bombs += 1
            else:
                grid.append('empty')
        if treasures == 0:
            grid[random.randint(0, 8)] = 'treasure'
            treasures = 1
        won = treasures >= 3
        points = self.calculate_points(won, 'treasure_hunt', {'treasures': treasures, 'username': username})
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'treasure_hunt', {'treasures': treasures})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'treasure_hunt')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, 0, 'treasure_hunt', check_achievements=False, gcoins_earned=final_points)
        self.add_game_history(username, 'treasure_hunt', won, final_points, f'找到{treasures}个宝藏 {bombs}个炸弹')
        self.update_daily_tasks(username, 'treasure_hunt', won)
        drops = self.roll_all_drops(username, 'treasure_hunt', won)
        remaining = self.get_remaining_plays(username)
        if amulet_used:
            remaining = remaining + 1
            bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        return {
            'success': True,
            'won': won,
            'grid': grid,
            'treasures': treasures,
            'bombs': bombs,
            'points_earned': final_points,
            'remaining_plays': remaining,
            'max_plays': max_plays,
            'is_member': is_game_member(self.users, username),
            'message': f'🎉 找到 {treasures} 个宝藏！' if won else f'😔 只找到 {treasures} 个宝藏，未达标',
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
            'drops': drops
        }

    def play_boss_battle(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        tier = get_member_tier(self.users, username)
        base_tier = _get_base_tier(tier)
        if base_tier not in ['supreme']:
            return {'success': False, 'error': '挑战BOSS是至尊会员专属游戏'}
        boss_hp = 150
        player_hp = 100
        damage_dealt = 0
        turn = 0
        combat_log = []
        while boss_hp > 0 and player_hp > 0 and turn < 20:
            turn += 1
            player_damage = random.randint(10, 30)
            crit = random.random() < 0.2
            if crit:
                player_damage = int(player_damage * 1.5)
            boss_hp -= player_damage
            damage_dealt += player_damage
            combat_log.append(f'回合{turn}: 你对BOSS造成 {player_damage} 伤害' + (' (暴击!)' if crit else ''))
            if boss_hp <= 0:
                break
            boss_damage = random.randint(8, 22)
            player_hp -= boss_damage
            combat_log.append(f'回合{turn}: BOSS对你造成 {boss_damage} 伤害')
        won = boss_hp <= 0
        points = self.calculate_points(won, 'boss_battle', {'damage': damage_dealt, 'username': username})
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'boss_battle', {'damage': damage_dealt})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'boss_battle')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, 0, 'boss_battle', check_achievements=False, gcoins_earned=final_points)
        self.add_game_history(username, 'boss_battle', won, final_points, f'造成{damage_dealt}伤害 剩余HP{max(0, boss_hp)}')
        self.update_daily_tasks(username, 'boss_battle', won)
        drops = self.roll_all_drops(username, 'boss_battle', won)
        remaining = self.get_remaining_plays(username)
        if amulet_used:
            remaining = remaining + 1
            bonus_message = (bonus_message + ' ' if bonus_message else '') + '🛡️ 护身符生效，本局不扣次数'
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        return {
            'success': True,
            'won': won,
            'boss_hp': max(0, boss_hp),
            'player_hp': max(0, player_hp),
            'damage_dealt': damage_dealt,
            'turns': turn,
            'combat_log': combat_log[-5:],
            'points_earned': final_points,
            'remaining_plays': remaining,
            'max_plays': max_plays,
            'is_member': is_game_member(self.users, username),
            'message': '🎉 击败BOSS！' if won else '😔 BOSS存活，挑战失败',
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': next((d for d in drops if d.get('type') == 'card'), None),
            'drops': drops
        }

    def get_stats(self, username):
        stats = self.get_user_game_stats(username)
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        tier = get_member_tier(self.users, username)
        win_streak = self.get_win_streak(username)
        level_info = self.get_user_level(username)
        title_info = self.get_user_title(username)
        expire_info = get_member_expire_info(self.users, username)
        gcoin_data = get_gcoin_data(self.users, username)
        if not stats:
            return {
                'today_plays': 0, 'max_plays': max_plays, 'remaining_plays': max_plays,
                'total_wins': 0, 'total_plays': 0, 'win_rate': 0,
                'today': self.get_today(),
                'is_member': is_game_member(self.users, username),
                'member_tier': tier,
                'member_tier_name': MEMBERSHIP_TIERS[tier]['name'],
                'member_bonus_rate': get_member_bonus_rate(self.users, username) * 100,
                'win_streak': win_streak, 'bonus_plays': bonus_plays,
                'level_info': level_info, 'title_info': title_info,
                'member_expire': expire_info,
                'gcoins': gcoin_data
            }
        return {
            'today_plays': stats.get('today_plays', 0),
            'max_plays': max_plays,
            'remaining_plays': max(0, max_plays - stats.get('today_plays', 0)),
            'total_wins': stats.get('total_wins', 0),
            'total_plays': stats.get('total_plays', 0),
            'win_rate': round(stats.get('total_wins', 0) / max(1, stats.get('total_plays', 0)) * 100, 1),
            'today': self.get_today(),
            'is_member': is_game_member(self.users, username),
            'member_tier': tier,
            'member_tier_name': MEMBERSHIP_TIERS[tier]['name'],
            'member_bonus_rate': get_member_bonus_rate(self.users, username) * 100,
            'win_streak': win_streak, 'bonus_plays': bonus_plays,
            'level_info': level_info, 'title_info': title_info,
            'member_expire': expire_info,
            'gcoins': gcoin_data
        }

    def get_game_list(self, username=None):
        base_games = [
            {'id': 'dice', 'name': '骰子大战', 'emoji': '🎲', 'description': '掷3个骰子比大小，支持猜单双/豹子', 'min_points': 5, 'max_points': 80, 'exclusive': False},
            {'id': 'blackjack', 'name': '二十一点', 'emoji': '🃏', 'description': '与庄家比21点，支持双倍/保险', 'min_points': 10, 'max_points': 110, 'exclusive': False},
            {'id': 'guess_number', 'name': '猜数字', 'emoji': '🎯', 'description': '1-100猜数字，可选难度', 'min_points': 8, 'max_points': 60, 'exclusive': False},
            {'id': 'rock_paper_scissors', 'name': '石头剪刀布', 'emoji': '🤖', 'description': '三局两胜', 'min_points': 3, 'max_points': 25, 'exclusive': False},
            {'id': 'roulette', 'name': '轮盘赌', 'emoji': '🎡', 'description': '猜数字/颜色/奇偶，支持组合下注', 'min_points': 8, 'max_points': 100, 'exclusive': False},
            {'id': 'whack_mole', 'name': '打地鼠', 'emoji': '🔨', 'description': '限时点击地鼠，难度可选', 'min_points': 8, 'max_points': 50, 'exclusive': False},
            {'id': 'lucky_wheel', 'name': '幸运转盘', 'emoji': '🎰', 'description': '转盘抽奖，最高x20倍率', 'min_points': 5, 'max_points': 80, 'exclusive': True},
            {'id': 'memory_cards', 'name': '记忆翻牌', 'emoji': '🧠', 'description': '翻牌配对，支持困难模式', 'min_points': 8, 'max_points': 108, 'exclusive': True},
            {'id': 'dice_royale', 'name': '骰子王者', 'emoji': '👑', 'description': '5颗骰子比大小，皇家骰翻倍', 'min_points': 30, 'max_points': 240, 'exclusive': True},
            {'id': 'blackjack_tournament', 'name': '21点锦标赛', 'emoji': '🏆', 'description': '连续3局21点对决，全胜翻倍', 'min_points': 50, 'max_points': 400, 'exclusive': True},
            {'id': 'treasure_hunt', 'name': '寻宝迷宫', 'emoji': '💎', 'description': '9宫格翻牌找宝藏，避开炸弹', 'min_points': 40, 'max_points': 360, 'exclusive': True},
            {'id': 'boss_battle', 'name': '挑战BOSS', 'emoji': '⚔️', 'description': '与BOSS回合制对战，高难度高回报', 'min_points': 60, 'max_points': 600, 'exclusive': True}
        ]
        if not username:
            return base_games
        exclusive_games = get_member_exclusive_games(self.users, username)
        result = []
        for g in base_games:
            if g['exclusive']:
                if g['id'] in exclusive_games:
                    result.append(g)
            else:
                result.append(g)
        return result

    def get_item_shop(self, username=None):
        items = []
        for item in ITEM_SHOP.values():
            item_copy = dict(item)
            if username:
                if item.get('member_only', False):
                    if not is_game_member(self.users, username):
                        item_copy['can_buy'] = False
                        item_copy['lock_reason'] = '会员专属'
                    else:
                        current_tier = get_member_tier(self.users, username)
                        min_tier = item.get('min_tier', 'none')
                        tier_order = {'none': 0, 'normal': 1, 'gold': 2, 'diamond': 3, 'supreme': 4}
                        current_base = _get_base_tier(current_tier)
                        if tier_order.get(current_base, 0) < tier_order.get(min_tier, 0):
                            item_copy['can_buy'] = False
                            item_copy['lock_reason'] = f'需要{MEMBERSHIP_TIERS.get(min_tier, {}).get("name", min_tier)}'
                        else:
                            item_copy['can_buy'] = True
                else:
                    item_copy['can_buy'] = True
            else:
                item_copy['can_buy'] = not item.get('member_only', False)
            items.append(item_copy)
        return items

    def migrate_game_stats(self, username):
        if username not in self.users:
            return False
        user_data = self.users[username]
        if 'game_stats' not in user_data:
            return False
        stats = user_data['game_stats']
        modified = False
        if 'today_wins' not in stats:
            stats['today_wins'] = 0
            modified = True
        if 'today_points' not in stats:
            stats['today_points'] = 0
            modified = True
        if 'game_plays' not in stats:
            stats['game_plays'] = {}
            modified = True
        if 'membership_coupon_count' not in stats:
            stats['membership_coupon_count'] = 0
            modified = True
        if 'membership_coupon_used' not in stats:
            stats['membership_coupon_used'] = 0
            modified = True
        if 'market_trades' not in stats:
            stats['market_trades'] = 0
            modified = True
        if 'auction_wins' not in stats:
            stats['auction_wins'] = 0
            modified = True
        if 'gcoins' not in user_data:
            user_data['gcoins'] = {'balance': 0, 'total_earned': 0, 'total_spent': 0}
            modified = True
        if 'game_plays' in stats and not stats['game_plays']:
            game_plays = {}
            history = user_data.get('game_history', [])
            for record in history:
                gid = record.get('game_id', '')
                if gid:
                    game_plays[gid] = game_plays.get(gid, 0) + 1
            for gid, gs in stats.get('game_wins', {}).items():
                if gid not in game_plays:
                    game_plays[gid] = gs
                elif game_plays[gid] < gs:
                    game_plays[gid] = gs
            if game_plays:
                stats['game_plays'] = game_plays
                modified = True
        return modified

    def get_user_level(self, username):
        if username not in self.users:
            return {'level': 1, 'name': '新手', 'icon': '🌱', 'next_level': 5, 'progress': 0}
        stats = self.get_user_game_stats(username)
        total_plays = stats.get('total_plays', 0) if stats else 0
        total_wins = stats.get('total_wins', 0) if stats else 0
        total_points = int(stats.get('total_points_earned', 0)) if stats else 0
        levels = LEVEL_SYSTEM['levels']
        current_level = levels[0]
        for lvl in levels:
            if total_plays >= lvl['min_plays'] and total_wins >= lvl['min_wins'] and total_points >= lvl['min_points']:
                current_level = lvl
        return {
            'level': current_level['level'],
            'name': current_level['name'],
            'icon': current_level['icon'],
            'total_plays': total_plays,
            'total_wins': total_wins,
            'total_points': total_points
        }

    def get_user_title(self, username):
        if username not in self.users:
            return {'id': '', 'name': '', 'icon': ''}
        user_data = self.users[username]
        chosen_title_id = user_data.get('chosen_title', '')
        titles = TITLE_SYSTEM['titles']
        unlocked_titles = self.get_unlocked_titles(username)
        unlocked_ids = [t['id'] for t in unlocked_titles]
        if chosen_title_id and chosen_title_id in unlocked_ids:
            for t in titles:
                if t['id'] == chosen_title_id:
                    return {'id': t['id'], 'name': t['name'], 'icon': t['icon']}
        if unlocked_titles:
            top_title = unlocked_titles[-1]
            return {'id': top_title['id'], 'name': top_title['name'], 'icon': top_title['icon']}
        return {'id': '', 'name': '', 'icon': ''}

    def get_unlocked_titles(self, username):
        if username not in self.users:
            return []
        stats = self.get_user_game_stats(username)
        if not stats:
            return []
        win_streak = self.get_win_streak(username)
        tier = get_member_tier(self.users, username)
        cards = self.get_user_cards(username)
        total_cards = 0
        for game_id, collection in CARD_COLLECTIONS.items():
            owned = cards.get(game_id, {})
            total_cards += len(owned)
        gcoin_data = get_gcoin_data(self.users, username)
        gcoins_total = gcoin_data.get('total_earned', 0) if gcoin_data else 0
        unlocked = []
        for title in TITLE_SYSTEM['titles']:
            cond_type = title['condition_type']
            cond_val = title['condition_value']
            matched = False
            if cond_type == 'total_plays':
                matched = stats.get('total_plays', 0) >= cond_val
            elif cond_type == 'total_wins':
                matched = stats.get('total_wins', 0) >= cond_val
            elif cond_type == 'max_win_streak':
                matched = win_streak.get('max_win', 0) >= cond_val
            elif cond_type.startswith('game_plays_'):
                game_id = cond_type.replace('game_plays_', '')
                matched = stats.get('game_plays', {}).get(game_id, 0) >= cond_val
            elif cond_type.startswith('game_wins_'):
                game_id = cond_type.replace('game_wins_', '')
                matched = stats.get('game_wins', {}).get(game_id, 0) >= cond_val
            elif cond_type == 'cards_total':
                matched = total_cards >= cond_val
            elif cond_type == 'tier':
                tier_order = {'none': 0, 'normal': 1, 'gold': 2, 'diamond': 3, 'supreme': 4}
                current_base = _get_base_tier(tier)
                matched = tier_order.get(current_base, 0) >= tier_order.get(cond_val, 0)
            elif cond_type == 'lucky_x20':
                matched = stats.get('lucky_x20', 0) >= cond_val
            elif cond_type == 'gcoins_total':
                matched = gcoins_total >= cond_val
            elif cond_type == 'market_trades':
                matched = stats.get('market_trades', 0) >= cond_val
            elif cond_type == 'auction_wins':
                matched = stats.get('auction_wins', 0) >= cond_val
            if matched:
                unlocked.append(title)
        return unlocked

    def set_user_title(self, username, title_id):
        if username not in self.users:
            return False, '用户不存在'
        unlocked_titles = self.get_unlocked_titles(username)
        unlocked_ids = [t['id'] for t in unlocked_titles]
        if title_id and title_id not in unlocked_ids:
            return False, '该称号尚未解锁'
        user_data = self.users[username]
        user_data['chosen_title'] = title_id
        self.save_users()
        return True, '称号已更换'

    def get_user_membership_coupons(self, username):
        return get_user_membership_coupons(self.users, username)

    def check_expiring_memberships(self):
        expiring = []
        for username in self.users:
            info = get_member_expire_info(self.users, username)
            if info.get('is_member') and info.get('is_expiring'):
                expiring.append({
                    'username': username,
                    'tier': get_member_tier(self.users, username),
                    'days_left': info.get('days_left', 0),
                    'hours_left': info.get('hours_left', 0),
                    'expires_at': info.get('expires_at', 0)
                })
        return expiring


game_manager = None


def init_game_manager(users_data, save_users_func, add_points_func, get_user_data_func):
    global game_manager
    game_manager = GameManager(users_data, save_users_func, add_points_func, get_user_data_func)
    return game_manager


def get_game_manager():
    return game_manager