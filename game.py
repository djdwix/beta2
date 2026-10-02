import random
import time
import json
from datetime import datetime, timedelta

MEMBERSHIP_PRICE = 288.88
NORMAL_MAX_PLAYS = 5
MEMBER_MAX_PLAYS = 10
MEMBER_BONUS_RATE = 0.30

MEMBERSHIP_TIERS = {
    'none': {
        'name': '普通用户',
        'price': 0,
        'max_plays': 5,
        'bonus_rate': 0.0,
        'daily_task_bonus': 0,
        'exclusive_games': []
    },
    'normal': {
        'name': '普通会员',
        'price': 288.88,
        'max_plays': 10,
        'bonus_rate': 0.30,
        'daily_task_bonus': 0,
        'exclusive_games': []
    },
    'gold': {
        'name': '黄金会员',
        'price': 588.88,
        'max_plays': 15,
        'bonus_rate': 0.50,
        'daily_task_bonus': 5,
        'exclusive_games': ['lucky_wheel']
    },
    'diamond': {
        'name': '钻石会员',
        'price': 1288.88,
        'max_plays': 50,
        'bonus_rate': 1.00,
        'daily_task_bonus': 10,
        'exclusive_games': ['lucky_wheel', 'memory_cards']
    },
    'supreme': {
        'name': '至尊会员',
        'price': 6888.00,
        'max_plays': 80,
        'bonus_rate': 3.00,
        'daily_task_bonus': 30,
        'exclusive_games': ['lucky_wheel', 'memory_cards'],
        'requirements': {
            'min_total_plays': 180,
            'min_win_rate': 72.0
        }
    }
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
    {'id': 'roulette_win', 'name': '轮盘赌赢一次', 'target': 1, 'reward': 6, 'type': 'roulette_win'}
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
    {'id': 'collect_all', 'name': '图鉴全收', 'desc': '收集全部卡牌', 'icon': '🏅', 'reward': 200, 'type': 'cards_total', 'target': 54},
    {'id': 'collect_set_dice', 'name': '骰子收藏', 'desc': '集齐骰子大战卡牌', 'icon': '🎲', 'reward': 30, 'type': 'cards_set_dice', 'target': 1},
    {'id': 'collect_set_blackjack', 'name': '扑克收藏', 'desc': '集齐二十一点卡牌', 'icon': '🃏', 'reward': 40, 'type': 'cards_set_blackjack', 'target': 1},
    {'id': 'collect_set_guess', 'name': '数字收藏', 'desc': '集齐猜数字卡牌', 'icon': '🎯', 'reward': 35, 'type': 'cards_set_guess_number', 'target': 1},
    {'id': 'collect_set_rps', 'name': '手势收藏', 'desc': '集齐石头剪刀布卡牌', 'icon': '🤖', 'reward': 25, 'type': 'cards_set_rock_paper_scissors', 'target': 1},
    {'id': 'collect_set_roulette', 'name': '轮盘收藏', 'desc': '集齐轮盘赌卡牌', 'icon': '🎡', 'reward': 35, 'type': 'cards_set_roulette', 'target': 1},
    {'id': 'collect_set_wheel', 'name': '转盘收藏', 'desc': '集齐幸运转盘卡牌', 'icon': '🎰', 'reward': 35, 'type': 'cards_set_lucky_wheel', 'target': 1},
    {'id': 'collect_set_memory', 'name': '记忆收藏', 'desc': '集齐记忆翻牌卡牌', 'icon': '🧠', 'reward': 35, 'type': 'cards_set_memory_cards', 'target': 1},
    {'id': 'whack_perfect', 'name': '打地鼠之神', 'desc': '打地鼠得分30', 'icon': '🔨', 'reward': 30, 'type': 'whack_score_30', 'target': 1}
]

ITEM_SHOP = {
    'lucky_charm': {
        'id': 'lucky_charm',
        'name': '幸运符',
        'icon': '🍀',
        'desc': '本局胜率+5%（游戏开始前使用）',
        'price': 5,
        'duration': 300,
        'games': ['dice', 'blackjack', 'roulette']
    },
    'double_card': {
        'id': 'double_card',
        'name': '双倍卡',
        'icon': '✨',
        'desc': '本局积分翻倍（游戏开始前使用）',
        'price': 15,
        'duration': 300,
        'games': []
    },
    'amulet': {
        'id': 'amulet',
        'name': '护身符',
        'icon': '🛡️',
        'desc': '本局输了不扣次数（游戏开始前使用）',
        'price': 10,
        'duration': 300,
        'games': []
    },
    'scope': {
        'id': 'scope',
        'name': '瞄准镜',
        'icon': '🎯',
        'desc': '打地鼠时间+10秒',
        'price': 20,
        'duration': 300,
        'games': ['whack_mole']
    },
    'triple_card': {
        'id': 'triple_card',
        'name': '积分三倍卡',
        'icon': '💎',
        'desc': '本局积分 ×3（比双倍卡更划算）',
        'price': 50,
        'duration': 300,
        'games': []
    },
    'extra_play': {
        'id': 'extra_play',
        'name': '免费次数券',
        'icon': '🎟️',
        'desc': '立即增加今日游戏次数+1（可叠加，最多5次）',
        'price': 40,
        'duration': 0,
        'games': []
    }
}

CHECKIN_REWARDS = [
    {'day': 1, 'reward_type': 'points', 'value': 1.0, 'icon': '💧', 'desc': '1积分'},
    {'day': 2, 'reward_type': 'points', 'value': 2.0, 'icon': '💧', 'desc': '2积分'},
    {'day': 3, 'reward_type': 'point_code', 'value': 1, 'icon': '🎫', 'desc': '普通积分卡密 x1'},
    {'day': 4, 'reward_type': 'points', 'value': 3.0, 'icon': '💧', 'desc': '3积分'},
    {'day': 5, 'reward_type': 'boost_code', 'value': 1, 'icon': '⚡', 'desc': '积分加成卡 x1'},
    {'day': 6, 'reward_type': 'points', 'value': 5.0, 'icon': '💰', 'desc': '5积分'},
    {'day': 7, 'reward_type': 'premium_point_code', 'value': 1, 'icon': '💎', 'desc': '高级积分卡密 x1'}
]

CHEST_REWARDS = [
    {'plays': 1, 'name': '青铜宝箱', 'icon': '🥉', 'points_min': 1, 'points_max': 3, 'item_chance': 0},
    {'plays': 3, 'name': '白银宝箱', 'icon': '🥈', 'points_min': 3, 'points_max': 6, 'item_chance': 0},
    {'plays': 5, 'name': '黄金宝箱', 'icon': '🥇', 'points_min': 6, 'points_max': 12, 'item_chance': 0.1},
    {'plays': 10, 'name': '钻石宝箱', 'icon': '💎', 'points_min': 15, 'points_max': 30, 'item_chance': 0.3},
    {'plays': 20, 'name': '传说宝箱', 'icon': '👑', 'points_min': 50, 'points_max': 80, 'item_chance': 1.0}
]

CARD_COLLECTIONS = {
    'dice': {
        'name': '骰子大战',
        'icon': '🎲',
        'cards': [
            {'id': 'd1', 'name': '一点', 'emoji': '⚀', 'rarity': 'common'},
            {'id': 'd2', 'name': '二点', 'emoji': '⚁', 'rarity': 'common'},
            {'id': 'd3', 'name': '三点', 'emoji': '⚂', 'rarity': 'common'},
            {'id': 'd4', 'name': '四点', 'emoji': '⚃', 'rarity': 'rare'},
            {'id': 'd5', 'name': '五点', 'emoji': '⚄', 'rarity': 'rare'},
            {'id': 'd6', 'name': '六点', 'emoji': '⚅', 'rarity': 'epic'}
        ]
    },
    'blackjack': {
        'name': '二十一点',
        'icon': '🃏',
        'cards': [
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
        ]
    },
    'guess_number': {
        'name': '猜数字',
        'icon': '🎯',
        'cards': [
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
        ]
    },
    'rock_paper_scissors': {
        'name': '石头剪刀布',
        'icon': '🤖',
        'cards': [
            {'id': 'rps_rock', 'name': '石头', 'emoji': '🪨', 'rarity': 'common'},
            {'id': 'rps_paper', 'name': '布', 'emoji': '📄', 'rarity': 'common'},
            {'id': 'rps_scissors', 'name': '剪刀', 'emoji': '✂️', 'rarity': 'rare'}
        ]
    },
    'roulette': {
        'name': '轮盘赌',
        'icon': '🎡',
        'cards': [
            {'id': 'r_red', 'name': '红色', 'emoji': '🔴', 'rarity': 'common'},
            {'id': 'r_black', 'name': '黑色', 'emoji': '⚫', 'rarity': 'common'},
            {'id': 'r_green', 'name': '绿色', 'emoji': '🟢', 'rarity': 'legendary'},
            {'id': 'r_even', 'name': '偶数', 'emoji': '2️⃣', 'rarity': 'rare'},
            {'id': 'r_odd', 'name': '奇数', 'emoji': '1️⃣', 'rarity': 'rare'},
            {'id': 'r_high', 'name': '大数', 'emoji': '⬆️', 'rarity': 'rare'},
            {'id': 'r_low', 'name': '小数', 'emoji': '⬇️', 'rarity': 'rare'},
            {'id': 'r_zero', 'name': '0', 'emoji': '0️⃣', 'rarity': 'epic'}
        ]
    },
    'lucky_wheel': {
        'name': '幸运转盘',
        'icon': '🎰',
        'cards': [
            {'id': 'w_pass', 'name': '谢谢参与', 'emoji': '🙏', 'rarity': 'common'},
            {'id': 'w_x1', 'name': 'x1', 'emoji': '1️⃣', 'rarity': 'common'},
            {'id': 'w_x2', 'name': 'x2', 'emoji': '2️⃣', 'rarity': 'common'},
            {'id': 'w_x3', 'name': 'x3', 'emoji': '3️⃣', 'rarity': 'rare'},
            {'id': 'w_x5', 'name': 'x5', 'emoji': '5️⃣', 'rarity': 'rare'},
            {'id': 'w_x8', 'name': 'x8', 'emoji': '8️⃣', 'rarity': 'epic'},
            {'id': 'w_x10', 'name': 'x10', 'emoji': '🔟', 'rarity': 'epic'},
            {'id': 'w_x20', 'name': 'x20', 'emoji': '💫', 'rarity': 'legendary'}
        ]
    },
    'memory_cards': {
        'name': '记忆翻牌',
        'icon': '🧠',
        'cards': [
            {'id': 'm_apple', 'name': '苹果', 'emoji': '🍎', 'rarity': 'common'},
            {'id': 'm_banana', 'name': '香蕉', 'emoji': '🍌', 'rarity': 'common'},
            {'id': 'm_grape', 'name': '葡萄', 'emoji': '🍇', 'rarity': 'common'},
            {'id': 'm_strawberry', 'name': '草莓', 'emoji': '🍓', 'rarity': 'rare'},
            {'id': 'm_cherry', 'name': '樱桃', 'emoji': '🍒', 'rarity': 'rare'},
            {'id': 'm_peach', 'name': '桃子', 'emoji': '🍑', 'rarity': 'epic'},
            {'id': 'm_kiwi', 'name': '猕猴桃', 'emoji': '🥝', 'rarity': 'epic'},
            {'id': 'm_pineapple', 'name': '菠萝', 'emoji': '🍍', 'rarity': 'legendary'}
        ]
    },
    'whack_mole': {
        'name': '打地鼠',
        'icon': '🔨',
        'cards': [
            {'id': 'wm_mole', 'name': '地鼠', 'emoji': '🐹', 'rarity': 'common'},
            {'id': 'wm_bomb', 'name': '炸弹', 'emoji': '💣', 'rarity': 'legendary'}
        ]
    }
}

CARD_RARITY_NAMES = {
    'common': '普通',
    'rare': '稀有',
    'epic': '史诗',
    'legendary': '传说'
}

CARD_RARITY_COLORS = {
    'common': '#9ca3af',
    'rare': '#60a5fa',
    'epic': '#a78bfa',
    'legendary': '#fbbf24'
}

CARD_RARITY_DISENCHANT = {
    'common': 1,
    'rare': 3,
    'epic': 8,
    'legendary': 20
}

CARD_DROP_RATES = {
    'common': 0.80,
    'rare': 0.15,
    'epic': 0.04,
    'legendary': 0.01
}


def get_membership_data(users, username):
    if username not in users:
        return None
    user_data = users[username]
    if 'membership' not in user_data:
        user_data['membership'] = {
            'is_member': False,
            'tier': 'none',
            'activated_at': 0,
            'expires_at': 0,
            'lifetime': True
        }
    if 'tier' not in user_data['membership']:
        if user_data['membership'].get('is_member', False):
            user_data['membership']['tier'] = 'normal'
        else:
            user_data['membership']['tier'] = 'none'
    return user_data['membership']


def is_game_member(users, username):
    membership = get_membership_data(users, username)
    if not membership:
        return False
    if membership.get('is_member', False):
        expires_at = membership.get('expires_at', 0)
        if expires_at == 0 or expires_at > int(time.time() * 1000):
            return True
        else:
            membership['is_member'] = False
            membership['tier'] = 'none'
            return False
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


def activate_game_membership(users, save_users_func, username, tier='normal'):
    if username not in users:
        return False, '用户不存在'
    if tier not in MEMBERSHIP_TIERS or tier == 'none':
        return False, '无效的会员等级'
    tier_info = MEMBERSHIP_TIERS[tier]
    price = tier_info['price']
    user_data = users[username]
    if tier == 'supreme':
        meets, total_plays, win_rate = check_supreme_requirements(users, username)
        if not meets:
            req = tier_info['requirements']
            return False, f'至尊会员需要总局数≥{req["min_total_plays"]}且胜率>{req["min_win_rate"]}%，当前{total_plays}局，胜率{win_rate}%'
    if user_data.get('totalPoints', 0) < price:
        return False, f'积分不足，需要 {price} 积分'
    current_tier = get_member_tier(users, username)
    if current_tier != 'none':
        return False, f'您已是{MEMBERSHIP_TIERS[current_tier]["name"]}'
    user_data['totalPoints'] = round(user_data['totalPoints'] - price, 2)
    if 'membership' not in user_data:
        user_data['membership'] = {}
    user_data['membership']['is_member'] = True
    user_data['membership']['tier'] = tier
    user_data['membership']['activated_at'] = int(time.time() * 1000)
    user_data['membership']['expires_at'] = 0
    user_data['membership']['lifetime'] = True
    if tier == 'supreme':
        user_data['membership']['supreme_snapshot'] = {
            'total_plays': total_plays,
            'win_rate': win_rate,
            'purchased_at': int(time.time() * 1000)
        }
    save_users_func()
    return True, f'{tier_info["name"]}开通成功！每日游戏次数提升至{tier_info["max_plays"]}次，获胜积分+{int(tier_info["bonus_rate"]*100)}%'


def upgrade_membership(users, save_users_func, username, new_tier):
    if username not in users:
        return False, '用户不存在'
    if new_tier not in MEMBERSHIP_TIERS or new_tier == 'none':
        return False, '无效的会员等级'
    current_tier = get_member_tier(users, username)
    tier_order = {'none': 0, 'normal': 1, 'gold': 2, 'diamond': 3, 'supreme': 4}
    if tier_order.get(new_tier, 0) <= tier_order.get(current_tier, 0):
        return False, '只能升级到更高等级'
    total_plays = 0
    win_rate = 0.0
    if new_tier == 'supreme':
        meets, total_plays, win_rate = check_supreme_requirements(users, username)
        if not meets:
            req = MEMBERSHIP_TIERS['supreme']['requirements']
            return False, f'至尊会员需要总局数≥{req["min_total_plays"]}且胜率>{req["min_win_rate"]}%，当前{total_plays}局，胜率{win_rate}%'
    current_price = MEMBERSHIP_TIERS.get(current_tier, MEMBERSHIP_TIERS['none'])['price']
    new_price = MEMBERSHIP_TIERS[new_tier]['price']
    upgrade_price = round(new_price - current_price, 2)
    user_data = users[username]
    if user_data.get('totalPoints', 0) < upgrade_price:
        return False, f'积分不足，升级需要 {upgrade_price} 积分'
    user_data['totalPoints'] = round(user_data['totalPoints'] - upgrade_price, 2)
    user_data['membership']['tier'] = new_tier
    user_data['membership']['is_member'] = True
    user_data['membership']['activated_at'] = int(time.time() * 1000)
    if new_tier == 'supreme':
        user_data['membership']['supreme_snapshot'] = {
            'total_plays': total_plays,
            'win_rate': win_rate,
            'purchased_at': int(time.time() * 1000)
        }
    save_users_func()
    tier_info = MEMBERSHIP_TIERS[new_tier]
    return True, f'升级成功！当前为{tier_info["name"]}，每日{tier_info["max_plays"]}次，+{int(tier_info["bonus_rate"]*100)}%'


def migrate_game_membership_data(users, save_users_func):
    modified = False
    for username, user_data in users.items():
        if 'membership' not in user_data:
            user_data['membership'] = {
                'is_member': False,
                'tier': 'none',
                'activated_at': 0,
                'expires_at': 0,
                'lifetime': True
            }
            modified = True
        else:
            membership = user_data['membership']
            if 'lifetime' not in membership:
                membership['lifetime'] = True
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
                if membership.get('is_member', False):
                    membership['tier'] = 'normal'
                else:
                    membership['tier'] = 'none'
                modified = True
    if modified:
        save_users_func()
    return modified


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
            'whack_mole': self.play_whack_mole
        }
        self.game_names = {
            'dice': '骰子大战',
            'blackjack': '二十一点',
            'guess_number': '猜数字',
            'rock_paper_scissors': '石头剪刀布',
            'roulette': '轮盘赌',
            'lucky_wheel': '幸运转盘',
            'memory_cards': '记忆翻牌',
            'whack_mole': '打地鼠'
        }
        self.guess_game_state = {}
        self.rps_game_state = {}
        self.memory_game_state = {}
        self.whack_game_state = {}

    def get_today(self):
        return datetime.now().strftime('%Y-%m-%d')

    def get_user_game_stats(self, username):
        if username not in self.users:
            return None
        user_data = self.users[username]
        if 'game_stats' not in user_data:
            user_data['game_stats'] = {
                'today_plays': 0,
                'today_date': '',
                'today_wins': 0,
                'today_points': 0,
                'total_wins': 0,
                'total_plays': 0,
                'total_points_earned': 0,
                'game_wins': {},
                'game_plays': {},
                'roulette_number_hits': 0,
                'memory_perfect': 0,
                'lucky_x20': 0,
                'whack_score_30': 0
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
            bonus_message = f'🔥 连赢{ws["current_win"]}局！额外+50%积分'
        elif ws['current_win'] >= 3:
            bonus_rate = 0.2
            bonus_message = f'🔥 连赢{ws["current_win"]}局！额外+20%积分'
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
                    {
                        'id': t['id'],
                        'name': t['name'],
                        'type': t['type'],
                        'target': t['target'],
                        'reward': t['reward'],
                        'game': t.get('game', ''),
                        'progress': 0,
                        'claimed': False
                    } for t in selected
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
                self.save_users()
                return True, f'领取成功！获得{reward}积分'
        return False, '任务不存在'

    def claim_all_daily_tasks(self, username):
        if username not in self.users:
            return False, '用户不存在', 0
        user_data = self.users[username]
        today = self.get_today()
        if 'daily_tasks' not in user_data or user_data['daily_tasks'].get('date') != today:
            return False, '今日任务未生成', 0
        all_tasks = user_data['daily_tasks']['tasks']
        total_tasks = len(all_tasks)
        already_claimed_all_before = all(
            t['claimed'] for t in all_tasks
        )
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
        self.save_users()
        truncated = len(details) >= max_details and total_cards_disenchanted > max_details
        return True, f'一键分解成功！共分解{total_cards_disenchanted}张重复卡牌，获得{total_points}积分', total_points, details, total_cards_disenchanted

    def roll_card_drop(self, username, game_id):
        if game_id not in CARD_COLLECTIONS:
            return None
        user_data = self.users[username]
        drop_chance = 0.30
        if is_game_member(self.users, username):
            drop_chance += 0.20
        if random.random() > drop_chance:
            return None
        cards_pool = CARD_COLLECTIONS[game_id]['cards']
        rarity_weights = []
        for card in cards_pool:
            rarity_weights.append(CARD_DROP_RATES[card['rarity']])
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
                'is_new': True,
                'card': selected,
                'rarity_name': CARD_RARITY_NAMES[selected['rarity']],
                'rarity_color': CARD_RARITY_COLORS[selected['rarity']],
                'message': f'🎉 获得新卡牌 {selected["emoji"]} {selected["name"]}（{CARD_RARITY_NAMES[selected["rarity"]]}）'
            }
        else:
            disenchant = CARD_RARITY_DISENCHANT[selected['rarity']]
            self.add_points(username, disenchant)
            return {
                'is_new': False,
                'card': selected,
                'rarity_name': CARD_RARITY_NAMES[selected['rarity']],
                'rarity_color': CARD_RARITY_COLORS[selected['rarity']],
                'disenchant_points': disenchant,
                'message': f'🎴 重复卡牌 {selected["emoji"]} {selected["name"]}，自动分解为 {disenchant} 积分'
            }

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
        self.save_users()
        return True, f'分解成功！获得{disenchant}积分', disenchant

    def _compute_achievement_progress(self, ach, stats, win_streak, tier, checkin, chest, daily_first, total_cards, sets_complete):
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
            progress = 1 if is_game_member(self.users, self._current_username) else 0
        elif ach['type'] == 'is_gold':
            progress = 1 if tier == 'gold' else 0
        elif ach['type'] == 'is_diamond':
            progress = 1 if tier == 'diamond' else 0
        elif ach['type'] == 'is_supreme':
            progress = 1 if tier == 'supreme' else 0
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
        return progress

    def _check_and_unlock_achievements(self, username):
        if username not in self.users:
            return
        self._current_username = username
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
            progress = self._compute_achievement_progress(ach, stats, win_streak, tier, checkin, chest, daily_first, total_cards, sets_complete)
            if progress >= ach['target']:
                unlocked[ach['id']] = {
                    'unlocked_at': int(time.time() * 1000),
                    'reward_claimed': False
                }
                changed = True
        if changed:
            self.save_users()

    def get_achievements(self, username, unlock=True):
        if username not in self.users:
            return {'achievements': [], 'unlocked_count': 0, 'total_count': len(ACHIEVEMENTS)}
        if unlock:
            self._check_and_unlock_achievements(username)
        self._current_username = username
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
            progress = self._compute_achievement_progress(ach, stats, win_streak, tier, checkin, chest, daily_first, total_cards, sets_complete)
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
        return {
            'achievements': result,
            'unlocked_count': unlocked_count,
            'total_count': len(ACHIEVEMENTS)
        }

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
        self.save_users()
        return True, f'领取成功！获得{reward}积分'

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
        self.save_users()
        return True, f'领取成功！共获得{total_reward}积分', total_reward

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
        user_data['active_items'][item_id] = {
            'expires_at': now + duration,
            'used_at': now
        }
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
            results.append({
                'username': username,
                'plays': plays,
                'wins': wins,
                'win_rate': win_rate,
                'points': points,
                'member_tier': tier
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
            game_stats[game_id] = {
                'name': game_name,
                'plays': 0,
                'wins': 0,
                'win_rate': 0
            }
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
            'game_stats': game_stats
        }

    def get_checkin_status(self, username):
        if username not in self.users:
            return None
        user_data = self.users[username]
        if 'checkin' not in user_data:
            user_data['checkin'] = {
                'last_date': '',
                'consecutive_days': 0,
                'total_days': 0,
                'claimed_today': False,
                'history': []
            }
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
        if checkin.get('claimed_today', False):
            next_day = day_index + 1 if day_index < 7 else 1
        else:
            next_day = day_index + 1 if day_index < 7 else 1
        rewards = []
        for i, r in enumerate(CHECKIN_REWARDS):
            day_num = i + 1
            if checkin.get('claimed_today', False):
                status = 'claimed' if day_num <= day_index else 'pending'
            else:
                status = 'claimed' if day_num < day_index else ('current' if day_num == day_index + 1 else 'pending')
            rewards.append({
                'day': day_num,
                'reward_type': r['reward_type'],
                'value': r['value'],
                'icon': r['icon'],
                'desc': r['desc'],
                'status': status
            })
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
            user_data['checkin'] = {
                'last_date': '',
                'consecutive_days': 0,
                'total_days': 0,
                'claimed_today': False,
                'history': []
            }
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
        checkin['history'].append({
            'date': today,
            'day': day_index,
            'reward': reward['desc']
        })
        if len(checkin['history']) > 90:
            checkin['history'] = checkin['history'][-90:]
        reward_msg = reward['desc']
        self.save_users()
        self._check_and_unlock_achievements(username)
        return True, f'签到成功！获得 {reward_msg}', reward

    def get_daily_first_win_status(self, username):
        if username not in self.users:
            return None
        user_data = self.users[username]
        if 'daily_first_win' not in user_data:
            user_data['daily_first_win'] = {
                'last_date': '',
                'claimed': False,
                'total_claimed': 0
            }
            self.save_users()
        dfw = user_data['daily_first_win']
        today = self.get_today()
        if dfw.get('last_date') != today:
            dfw['claimed'] = False
            dfw['last_date'] = today
            self.save_users()
        return {
            'claimed': dfw.get('claimed', False),
            'total_claimed': dfw.get('total_claimed', 0),
            'reward': 5
        }

    def claim_daily_first_win(self, username):
        if username not in self.users:
            return False, '用户不存在'
        user_data = self.users[username]
        if 'daily_first_win' not in user_data:
            user_data['daily_first_win'] = {
                'last_date': '',
                'claimed': False,
                'total_claimed': 0
            }
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
        self.save_users()
        self._check_and_unlock_achievements(username)
        return True, '领取成功！获得 5 积分'

    def get_chest_status(self, username):
        if username not in self.users:
            return None
        user_data = self.users[username]
        if 'chests' not in user_data:
            user_data['chests'] = {
                'date': '',
                'opened': [],
                'streak_all_days': 0,
                'last_full_open_date': ''
            }
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
        chests.setdefault('opened', []).append(chest_plays)
        self.add_points(username, points)
        item_reward = None
        if chest_info.get('item_chance', 0) > 0 and random.random() < chest_info['item_chance']:
            item_id = random.choice(list(ITEM_SHOP.keys()))
            if 'items' not in user_data:
                user_data['items'] = {}
            if item_id not in user_data['items']:
                user_data['items'][item_id] = {
                    'id': item_id,
                    'name': ITEM_SHOP[item_id]['name'],
                    'icon': ITEM_SHOP[item_id]['icon'],
                    'desc': ITEM_SHOP[item_id]['desc'],
                    'count': 0,
                    'expires_at': 0
                }
            user_data['items'][item_id]['count'] = user_data['items'][item_id].get('count', 0) + 1
            item_reward = ITEM_SHOP[item_id]['name']
        self.save_users()
        self._check_and_unlock_achievements(username)
        if item_reward:
            return True, f'开启{chest_info["name"]}，获得 {points} 积分 + {item_reward} x1', points, item_reward
        return True, f'开启{chest_info["name"]}，获得 {points} 积分', points, None

    def get_daily_bonus_status(self, username):
        if username not in self.users:
            return None
        user_data = self.users[username]
        if 'daily_bonus' not in user_data:
            user_data['daily_bonus'] = {
                'last_date': '',
                'spins': 0,
                'used_free': False
            }
            self.save_users()
        db = user_data['daily_bonus']
        today = self.get_today()
        if db.get('last_date') != today:
            db['last_date'] = today
            db['used_free'] = False
            db['spins'] = 0
            self.save_users()
        return {
            'used_free': db.get('used_free', False),
            'can_spin': not db.get('used_free', False),
            'spins': db.get('spins', 0)
        }

    def spin_daily_bonus(self, username):
        if username not in self.users:
            return False, '用户不存在', None
        user_data = self.users[username]
        if 'daily_bonus' not in user_data:
            user_data['daily_bonus'] = {
                'last_date': '',
                'spins': 0,
                'used_free': False
            }
        db = user_data['daily_bonus']
        today = self.get_today()
        if db.get('last_date') != today:
            db['last_date'] = today
            db['used_free'] = False
            db['spins'] = 0
        if db.get('used_free', False):
            return False, '今日免费抽奖已用完', None
        rewards = [
            {'icon': '💧', 'name': '1积分', 'points': 1, 'weight': 30},
            {'icon': '💧', 'name': '2积分', 'points': 2, 'weight': 25},
            {'icon': '💰', 'name': '3积分', 'points': 3, 'weight': 20},
            {'icon': '💰', 'name': '5积分', 'points': 5, 'weight': 15},
            {'icon': '💎', 'name': '8积分', 'points': 8, 'weight': 8},
            {'icon': '🌟', 'name': '15积分', 'points': 15, 'weight': 2}
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
        self.save_users()
        return True, f'恭喜获得 {selected["name"]}', selected

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

    def record_play(self, username, won, points_earned, game_id='', check_achievements=True):
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
            'dice': (5, 25),
            'blackjack': (10, 50),
            'guess_number': (8, 35),
            'rock_paper_scissors': (3, 15),
            'roulette': (15, 100),
            'lucky_wheel': (10, 80),
            'memory_cards': (10, 60),
            'whack_mole': (8, 35)
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
                base_min, base_max = 25, 35
            elif score >= 15:
                base_min, base_max = 15, 25
            else:
                base_min, base_max = 8, 15
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
            bonus_message = f'{streak["bonus_message"]}（+{bonus_points}积分）'
        if not won and streak.get('current_lose', 0) >= 3:
            consolation = 2
            final_points = consolation
            bonus_message = f'💪 连败{streak["current_lose"]}局，获得安慰奖励+{consolation}积分'
            won = True
        return final_points, bonus_message, streak

    def apply_active_items(self, username, won, points, game_id):
        effects = self.get_active_effects(username)
        extra_message = ''
        if 'triple_card' in effects and won:
            points = points * 3
            extra_message = '💎 积分三倍卡生效！积分 ×3'
            self.consume_effects(username, 'triple_card', persist=False)
        elif 'double_card' in effects and won:
            points = points * 2
            extra_message = '✨ 双倍卡生效！积分翻倍'
            self.consume_effects(username, 'double_card', persist=False)
        if 'lucky_charm' in effects and game_id in ITEM_SHOP['lucky_charm']['games']:
            self.consume_effects(username, 'lucky_charm', persist=False)
        return points, extra_message

    def check_amulet(self, username, won):
        effects = self.get_active_effects(username)
        if not won and 'amulet' in effects:
            self.consume_effects(username, 'amulet', persist=False)
            return True
        return False

    def play_dice(self, username, bet_type='high', bet_value=7):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
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
        else:
            won = player_total > ai_total
        diff = abs(player_total - ai_total)
        points = self.calculate_points(won, 'dice', {'diff': diff, 'username': username})
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'dice', {'diff': diff})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'dice')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, final_points, 'dice', check_achievements=False)
        self.add_game_history(username, 'dice', won, final_points, f'你{player_total} vs AI{ai_total}')
        self.update_daily_tasks(username, 'dice', won)
        card_drop = self.roll_card_drop(username, 'dice')
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
            'message': '🎉 你赢了！' if won else '😔 你输了！',
            'diff': diff,
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': card_drop
        }

    def play_blackjack(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
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
        dealer_hit_count = 0
        while dealer_total < 17:
            dealer_hand.append(deck.pop())
            dealer_total = hand_total(dealer_hand)
            dealer_hit_count += 1
        if player_total > 21:
            won = False
        elif dealer_total > 21:
            won = True
        elif player_total > dealer_total:
            won = True
        elif player_total == dealer_total:
            won = False
        else:
            won = False
        points = self.calculate_points(won, 'blackjack', {'player_total': player_total, 'dealer_total': dealer_total, 'username': username})
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'blackjack', {'player_total': player_total, 'dealer_total': dealer_total})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'blackjack')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, final_points, 'blackjack', check_achievements=False)
        self.add_game_history(username, 'blackjack', won, final_points, f'你{player_total} vs 庄家{dealer_total}')
        self.update_daily_tasks(username, 'blackjack', won)
        card_drop = self.roll_card_drop(username, 'blackjack')
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
            'message': '🎉 你赢了！' if won else '😔 你输了！',
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': card_drop
        }

    def start_guess_game(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        secret = random.randint(1, 100)
        self.guess_game_state[username] = {
            'secret': secret,
            'attempts': 0,
            'max_attempts': 7,
            'hints': [],
            'active': True,
            'game_started': True,
            'started_at': int(time.time() * 1000)
        }
        if username in self.users:
            self.users[username]['guess_state'] = self.guess_game_state[username]
            self.save_users()
        return {
            'success': True,
            'max_attempts': 7,
            'message': '🎯 游戏已开始！1-100之间猜一个数字，你有7次机会'
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
        state['attempts'] += 1
        secret = state['secret']
        if guess == secret:
            points = self.calculate_points(True, 'guess_number', {'attempts': state['attempts'], 'username': username})
            final_points, bonus_message, streak = self.apply_streak_and_consolation(username, True, points, 'guess_number', {'attempts': state['attempts']})
            final_points, item_message = self.apply_active_items(username, True, final_points, 'guess_number')
            self.record_play(username, True, final_points, 'guess_number', check_achievements=False)
            self.add_game_history(username, 'guess_number', True, final_points, f'{state["attempts"]}次猜中')
            self.update_daily_tasks(username, 'guess_number', True, {'attempts': state['attempts']})
            card_drop = self.roll_card_drop(username, 'guess_number')
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
                'card_drop': card_drop
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
            self.record_play(username, False, final_points, 'guess_number', check_achievements=False)
            self.add_game_history(username, 'guess_number', False, final_points, f'未猜中，答案{secret}')
            self.update_daily_tasks(username, 'guess_number', False)
            card_drop = self.roll_card_drop(username, 'guess_number')
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
                'card_drop': card_drop
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

    def play_guess_number(self, username, guess=None):
        if guess is None:
            return self.start_guess_game(username)
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
            'player_wins': 0,
            'ai_wins': 0,
            'rounds_played': 0,
            'round_history': [],
            'active': True,
            'best_of': 3,
            'game_started': True,
            'started_at': int(time.time() * 1000)
        }
        if username in self.users:
            self.users[username]['rps_state'] = self.rps_game_state[username]
            self.save_users()
        return {
            'success': True,
            'waiting': True,
            'message': '🤖 游戏已开始！请选择出拳：🪨 石头 | 📄 布 | ✂️ 剪刀'
        }

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
            self.record_play(username, won, final_points, 'rock_paper_scissors', check_achievements=False)
            self.add_game_history(username, 'rock_paper_scissors', won, final_points, f'比分 {state["player_wins"]}:{state["ai_wins"]}')
            self.update_daily_tasks(username, 'rock_paper_scissors', won)
            card_drop = self.roll_card_drop(username, 'rock_paper_scissors')
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
                'card_drop': card_drop
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

    def play_roulette(self, username, bet_type='number', bet_value=0):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        numbers = list(range(0, 37))
        red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
        black_numbers = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
        result = random.choice(numbers)
        multiplier = 1
        won = False
        win_desc = ''
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
        self.record_play(username, won, final_points, 'roulette', check_achievements=False)
        self.add_game_history(username, 'roulette', won, final_points, f'结果{result} {color} 下注{bet_type}')
        self.update_daily_tasks(username, 'roulette', won)
        card_drop = self.roll_card_drop(username, 'roulette')
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
            'multiplier': multiplier,
            'win_desc': win_desc,
            'points_earned': final_points,
            'remaining_plays': remaining,
            'max_plays': max_plays,
            'is_member': is_game_member(self.users, username),
            'message': '🎉 你赢了！' + (win_desc if win_desc else '') if won else '😔 你输了！',
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': card_drop
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
        if tier not in ['gold', 'diamond', 'supreme']:
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
        self.record_play(username, won, final_points, 'lucky_wheel', check_achievements=False)
        self.add_game_history(username, 'lucky_wheel', won, final_points, f'转盘结果 {selected["label"]}')
        self.update_daily_tasks(username, 'lucky_wheel', won)
        card_drop = self.roll_card_drop(username, 'lucky_wheel')
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
            'card_drop': card_drop
        }

    def start_memory_game(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        tier = get_member_tier(self.users, username)
        if tier not in ['diamond', 'supreme']:
            return {'success': False, 'error': '记忆翻牌是钻石会员及以上专属游戏'}
        symbols = ['🍎', '🍌', '🍇', '🍓', '🍒', '🍑', '🥝', '🍍']
        cards = symbols + symbols
        random.shuffle(cards)
        self.memory_game_state[username] = {
            'cards': cards,
            'flipped': [],
            'matched': [],
            'moves': 0,
            'active': True,
            'started_at': int(time.time() * 1000)
        }
        if username in self.users:
            self.users[username]['memory_state'] = {
                'cards': cards,
                'flipped': [],
                'matched': [],
                'moves': 0,
                'active': True,
                'started_at': int(time.time() * 1000)
            }
            self.save_users()
        return {
            'success': True,
            'cards': cards,
            'total_pairs': 8,
            'message': '🃏 游戏开始！翻开两张相同的牌即可配对'
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
        if index < 0 or index >= 16:
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
        card_drop = None
        if len(state['flipped']) == 2:
            state['moves'] += 1
            i1, i2 = state['flipped']
            if state['cards'][i1] == state['cards'][i2]:
                state['matched'].extend([i1, i2])
                state['flipped'] = []
                is_match = True
                if len(state['matched']) == 16:
                    state['active'] = False
                    game_over = True
                    points = self.calculate_points(True, 'memory_cards', {'moves': state['moves'], 'username': username})
                    final_points, bonus_message, streak = self.apply_streak_and_consolation(username, True, points, 'memory_cards', {'moves': state['moves']})
                    if state['moves'] <= 15:
                        stats = self.get_user_game_stats(username)
                        stats['memory_perfect'] = stats.get('memory_perfect', 0) + 1
                        self.save_users()
                    final_points, item_message = self.apply_active_items(username, True, final_points, 'memory_cards')
                    if item_message:
                        bonus_message = (bonus_message + ' ' if bonus_message else '') + item_message
                    self.record_play(username, True, final_points, 'memory_cards', check_achievements=False)
                    self.add_game_history(username, 'memory_cards', True, final_points, f'{state["moves"]}步完成')
                    self.update_daily_tasks(username, 'memory_cards', True)
                    card_drop = self.roll_card_drop(username, 'memory_cards')
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
                'message': f'🎉 全部配对成功！用了{state["moves"]}步，获得{final_points}积分',
                'win_streak': streak.get('current_win', 0),
                'lose_streak': streak.get('current_lose', 0),
                'bonus_message': bonus_message,
                'card_drop': card_drop
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

    def play_memory_cards(self, username, action=None, index=None):
        if action == 'start' or action is None:
            return self.start_memory_game(username)
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

    def start_whack_game(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        effects = self.get_active_effects(username)
        has_scope = 'scope' in effects
        if has_scope:
            self.consume_effects(username, 'scope', persist=False)
        duration = 40 if has_scope else 30
        self.whack_game_state[username] = {
            'score': 0,
            'hits': 0,
            'bombs': 0,
            'active': True,
            'duration': duration,
            'started_at': int(time.time() * 1000),
            'has_scope': has_scope
        }
        if username in self.users:
            self.users[username]['whack_state'] = self.whack_game_state[username]
            self.save_users()
        return {
            'success': True,
            'duration': duration,
            'has_scope': has_scope,
            'message': '🔨 游戏开始！30秒内点击地鼠，避开炸弹' + ('（瞄准镜已生效：+10秒）' if has_scope else '')
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
        return {
            'success': True,
            'score': score,
            'hits': hits,
            'bombs': bombs,
            'active': True
        }

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
        if final_score >= 30:
            stats = self.get_user_game_stats(username)
            stats['whack_score_30'] = stats.get('whack_score_30', 0) + 1
            self.save_users()
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'whack_mole', {'score': final_score})
        if bonus_message and not won:
            won = True
        final_points, item_message = self.apply_active_items(username, won, final_points, 'whack_mole')
        amulet_used = self.check_amulet(username, won)
        self.record_play(username, won, final_points, 'whack_mole', check_achievements=False)
        self.add_game_history(username, 'whack_mole', won, final_points, f'得分{final_score} 打中{hits} 炸弹{bombs}')
        self.update_daily_tasks(username, 'whack_mole', won)
        card_drop = self.roll_card_drop(username, 'whack_mole')
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
            'message': f'🎉 得分 {final_score}！' if won else '😔 得分 0，未获得积分',
            'win_streak': streak.get('current_win', 0),
            'lose_streak': streak.get('current_lose', 0),
            'bonus_message': (bonus_message + ' ' if bonus_message else '') + item_message,
            'card_drop': card_drop
        }

    def play_whack_mole(self, username, action=None, score=0, hits=0, bombs=0):
        if action == 'start' or action is None:
            return self.start_whack_game(username)
        if action == 'hit':
            return self.whack_hit(username, score, hits, bombs)
        if action == 'finish':
            return self.finish_whack_game(username, score, hits, bombs)
        return {'success': False, 'error': '无效的操作'}

    def get_stats(self, username):
        stats = self.get_user_game_stats(username)
        user_data = self.users.get(username, {})
        bonus_plays = user_data.get('bonus_plays', 0)
        max_plays = get_member_max_plays(self.users, username) + bonus_plays
        tier = get_member_tier(self.users, username)
        win_streak = self.get_win_streak(username)
        if not stats:
            return {
                'today_plays': 0,
                'max_plays': max_plays,
                'remaining_plays': max_plays,
                'total_wins': 0,
                'total_plays': 0,
                'win_rate': 0,
                'today': self.get_today(),
                'is_member': is_game_member(self.users, username),
                'member_tier': tier,
                'member_tier_name': MEMBERSHIP_TIERS[tier]['name'],
                'member_bonus_rate': get_member_bonus_rate(self.users, username) * 100,
                'win_streak': win_streak,
                'bonus_plays': bonus_plays
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
            'win_streak': win_streak,
            'bonus_plays': bonus_plays
        }

    def get_game_list(self, username=None):
        base_games = [
            {'id': 'dice', 'name': '骰子大战', 'emoji': '🎲', 'description': '掷3个骰子比大小', 'min_points': 5, 'max_points': 40, 'exclusive': False},
            {'id': 'blackjack', 'name': '二十一点', 'emoji': '🃏', 'description': '与庄家比21点', 'min_points': 10, 'max_points': 55, 'exclusive': False},
            {'id': 'guess_number', 'name': '猜数字', 'emoji': '🎯', 'description': '1-100猜数字，7次机会', 'min_points': 8, 'max_points': 45, 'exclusive': False},
            {'id': 'rock_paper_scissors', 'name': '石头剪刀布', 'emoji': '🤖', 'description': '三局两胜', 'min_points': 3, 'max_points': 25, 'exclusive': False},
            {'id': 'roulette', 'name': '轮盘赌', 'emoji': '🎡', 'description': '猜数字/颜色/奇偶', 'min_points': 8, 'max_points': 100, 'exclusive': False},
            {'id': 'whack_mole', 'name': '打地鼠', 'emoji': '🔨', 'description': '30秒限时点击地鼠', 'min_points': 8, 'max_points': 35, 'exclusive': False},
            {'id': 'lucky_wheel', 'name': '幸运转盘', 'emoji': '🎰', 'description': '转盘抽奖，最高x20倍率', 'min_points': 5, 'max_points': 80, 'exclusive': True},
            {'id': 'memory_cards', 'name': '记忆翻牌', 'emoji': '🧠', 'description': '翻牌配对，步数越少分越高', 'min_points': 8, 'max_points': 60, 'exclusive': True}
        ]
        if not username:
            return base_games
        exclusive_games = get_member_exclusive_games(self.users, username)
        tier = get_member_tier(self.users, username)
        result = []
        for g in base_games:
            if g['exclusive']:
                if g['id'] in exclusive_games:
                    result.append(g)
            else:
                result.append(g)
        return result

    def get_item_shop(self):
        return list(ITEM_SHOP.values())

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


game_manager = None


def init_game_manager(users_data, save_users_func, add_points_func, get_user_data_func):
    global game_manager
    game_manager = GameManager(users_data, save_users_func, add_points_func, get_user_data_func)
    return game_manager


def get_game_manager():
    return game_manager