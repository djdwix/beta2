import random
import time
import json
from datetime import datetime

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
    {'id': 'win_streak_2', 'name': '连赢2局', 'target': 2, 'reward': 8, 'type': 'win_streak'},
    {'id': 'guess_win_fast', 'name': '猜数字5次内猜中', 'target': 1, 'reward': 8, 'type': 'guess_fast'},
    {'id': 'roulette_win', 'name': '轮盘赌赢一次', 'target': 1, 'reward': 6, 'type': 'roulette_win'}
]


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


def activate_game_membership(users, save_users_func, username, tier='normal'):
    if username not in users:
        return False, '用户不存在'
    if tier not in MEMBERSHIP_TIERS or tier == 'none':
        return False, '无效的会员等级'
    tier_info = MEMBERSHIP_TIERS[tier]
    price = tier_info['price']
    user_data = users[username]
    if user_data.get('totalPoints', 0) < price:
        return False, f'积分不足，需要 {price} 积分'
    current_tier = get_member_tier(users, username)
    if current_tier != 'none':
        return False, f'您已是{tier_info["name"]}'
    user_data['totalPoints'] = round(user_data['totalPoints'] - price, 2)
    if 'membership' not in user_data:
        user_data['membership'] = {}
    user_data['membership']['is_member'] = True
    user_data['membership']['tier'] = tier
    user_data['membership']['activated_at'] = int(time.time() * 1000)
    user_data['membership']['expires_at'] = 0
    user_data['membership']['lifetime'] = True
    save_users_func()
    return True, f'{tier_info["name"]}开通成功！每日游戏次数提升至{tier_info["max_plays"]}次，获胜积分+{int(tier_info["bonus_rate"]*100)}%'


def upgrade_membership(users, save_users_func, username, new_tier):
    if username not in users:
        return False, '用户不存在'
    if new_tier not in MEMBERSHIP_TIERS or new_tier == 'none':
        return False, '无效的会员等级'
    current_tier = get_member_tier(users, username)
    tier_order = {'none': 0, 'normal': 1, 'gold': 2, 'diamond': 3}
    if tier_order.get(new_tier, 0) <= tier_order.get(current_tier, 0):
        return False, '只能升级到更高等级'
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
            'memory_cards': self.play_memory_cards
        }
        self.game_names = {
            'dice': '骰子大战',
            'blackjack': '二十一点',
            'guess_number': '猜数字',
            'rock_paper_scissors': '石头剪刀布',
            'roulette': '轮盘赌',
            'lucky_wheel': '幸运转盘',
            'memory_cards': '记忆翻牌'
        }
        self.guess_game_state = {}
        self.rps_game_state = {}
        self.memory_game_state = {}

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
                'total_wins': 0,
                'total_plays': 0
            }
        stats = user_data['game_stats']
        today = self.get_today()
        if stats.get('today_date') != today:
            stats['today_plays'] = 0
            stats['today_date'] = today
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
            return {'current_win': 0, 'current_lose': 0, 'max_win': 0}
        user_data = self.users[username]
        if 'win_streak' not in user_data:
            user_data['win_streak'] = {'current_win': 0, 'current_lose': 0, 'max_win': 0}
        return user_data['win_streak']

    def update_win_streak(self, username, won):
        if username not in self.users:
            return {'current_win': 0, 'current_lose': 0, 'max_win': 0, 'bonus_rate': 0, 'bonus_message': ''}
        user_data = self.users[username]
        if 'win_streak' not in user_data:
            user_data['win_streak'] = {'current_win': 0, 'current_lose': 0, 'max_win': 0}
        ws = user_data['win_streak']
        if won:
            ws['current_win'] = ws.get('current_win', 0) + 1
            ws['current_lose'] = 0
            if ws['current_win'] > ws.get('max_win', 0):
                ws['max_win'] = ws['current_win']
        else:
            ws['current_lose'] = ws.get('current_lose', 0) + 1
            ws['current_win'] = 0
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
                ws = self.get_win_streak(username)
                if ws.get('current_win', 0) >= task['target']:
                    task['progress'] = task['target']
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
        total_reward = 0
        claimed_count = 0
        for task in user_data['daily_tasks']['tasks']:
            if task['progress'] >= task['target'] and not task['claimed']:
                task['claimed'] = True
                total_reward += task['reward']
                claimed_count += 1
        if claimed_count == 0:
            return False, '没有可领取的任务', 0
        completed = sum(1 for t in user_data['daily_tasks']['tasks'] if t['progress'] >= t['target'])
        if completed >= len(user_data['daily_tasks']['tasks']) and not user_data['daily_tasks'].get('bonus_claimed', False):
            tier_bonus = get_member_daily_task_bonus(self.users, username)
            extra_bonus = 15 + tier_bonus
            total_reward += extra_bonus
            user_data['daily_tasks']['bonus_claimed'] = True
        self.add_points(username, total_reward)
        self.save_users()
        return True, f'领取成功！共获得{total_reward}积分', total_reward

    def can_play(self, username):
        stats = self.get_user_game_stats(username)
        if not stats:
            return False
        max_plays = get_member_max_plays(self.users, username)
        return stats.get('today_plays', 0) < max_plays

    def get_remaining_plays(self, username):
        stats = self.get_user_game_stats(username)
        if not stats:
            return 0
        max_plays = get_member_max_plays(self.users, username)
        return max(0, max_plays - stats.get('today_plays', 0))

    def record_play(self, username, won, points_earned):
        stats = self.get_user_game_stats(username)
        if not stats:
            return None
        stats['today_plays'] = stats.get('today_plays', 0) + 1
        stats['total_plays'] = stats.get('total_plays', 0) + 1
        if won:
            stats['total_wins'] = stats.get('total_wins', 0) + 1
        self.save_users()
        if points_earned > 0 and won:
            self.add_points(username, points_earned)
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
            'memory_cards': (10, 60)
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
        self.record_play(username, won, final_points)
        self.add_game_history(username, 'dice', won, final_points, f'你{player_total} vs AI{ai_total}')
        self.update_daily_tasks(username, 'dice', won)
        remaining = self.get_remaining_plays(username)
        max_plays = get_member_max_plays(self.users, username)
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
            'bonus_message': bonus_message
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
        self.record_play(username, won, final_points)
        self.add_game_history(username, 'blackjack', won, final_points, f'你{player_total} vs 庄家{dealer_total}')
        self.update_daily_tasks(username, 'blackjack', won)
        remaining = self.get_remaining_plays(username)
        max_plays = get_member_max_plays(self.users, username)
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
            'bonus_message': bonus_message
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
            self.record_play(username, True, final_points)
            self.add_game_history(username, 'guess_number', True, final_points, f'{state["attempts"]}次猜中')
            self.update_daily_tasks(username, 'guess_number', True, {'attempts': state['attempts']})
            remaining = self.get_remaining_plays(username)
            max_plays = get_member_max_plays(self.users, username)
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
                'bonus_message': bonus_message
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
            self.record_play(username, False, final_points)
            self.add_game_history(username, 'guess_number', False, final_points, f'未猜中，答案{secret}')
            self.update_daily_tasks(username, 'guess_number', False)
            remaining = self.get_remaining_plays(username)
            max_plays = get_member_max_plays(self.users, username)
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
                'bonus_message': bonus_message
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
            self.record_play(username, won, final_points)
            self.add_game_history(username, 'rock_paper_scissors', won, final_points, f'比分 {state["player_wins"]}:{state["ai_wins"]}')
            self.update_daily_tasks(username, 'rock_paper_scissors', won)
            remaining = self.get_remaining_plays(username)
            max_plays = get_member_max_plays(self.users, username)
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
                'bonus_message': bonus_message
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
        self.record_play(username, won, final_points)
        self.add_game_history(username, 'roulette', won, final_points, f'结果{result} {color} 下注{bet_type}')
        self.update_daily_tasks(username, 'roulette', won)
        remaining = self.get_remaining_plays(username)
        max_plays = get_member_max_plays(self.users, username)
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
            'bonus_message': bonus_message
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
        if tier not in ['gold', 'diamond']:
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
        final_points, bonus_message, streak = self.apply_streak_and_consolation(username, won, points, 'lucky_wheel', {'multiplier': selected['multiplier']})
        if bonus_message and not won:
            won = True
        self.record_play(username, won, final_points)
        self.add_game_history(username, 'lucky_wheel', won, final_points, f'转盘结果 {selected["label"]}')
        self.update_daily_tasks(username, 'lucky_wheel', won)
        remaining = self.get_remaining_plays(username)
        max_plays = get_member_max_plays(self.users, username)
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
            'bonus_message': bonus_message
        }

    def start_memory_game(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限', 'remaining': 0}
        tier = get_member_tier(self.users, username)
        if tier != 'diamond':
            return {'success': False, 'error': '记忆翻牌是钻石会员专属游戏'}
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
                    self.record_play(username, True, final_points)
                    self.add_game_history(username, 'memory_cards', True, final_points, f'{state["moves"]}步完成')
                    self.update_daily_tasks(username, 'memory_cards', True)
        if username in self.users:
            self.users[username]['memory_state'] = state
            self.save_users()
        if game_over:
            remaining = self.get_remaining_plays(username)
            max_plays = get_member_max_plays(self.users, username)
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
                'bonus_message': bonus_message
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

    def get_stats(self, username):
        stats = self.get_user_game_stats(username)
        max_plays = get_member_max_plays(self.users, username)
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
                'win_streak': win_streak
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
            'win_streak': win_streak
        }

    def get_game_list(self, username=None):
        base_games = [
            {'id': 'dice', 'name': '骰子大战', 'emoji': '🎲', 'description': '掷3个骰子比大小', 'min_points': 5, 'max_points': 40, 'exclusive': False},
            {'id': 'blackjack', 'name': '二十一点', 'emoji': '🃏', 'description': '与庄家比21点', 'min_points': 10, 'max_points': 55, 'exclusive': False},
            {'id': 'guess_number', 'name': '猜数字', 'emoji': '🎯', 'description': '1-100猜数字，7次机会', 'min_points': 8, 'max_points': 45, 'exclusive': False},
            {'id': 'rock_paper_scissors', 'name': '石头剪刀布', 'emoji': '🤖', 'description': '三局两胜', 'min_points': 3, 'max_points': 25, 'exclusive': False},
            {'id': 'roulette', 'name': '轮盘赌', 'emoji': '🎡', 'description': '猜数字/颜色/奇偶', 'min_points': 8, 'max_points': 100, 'exclusive': False},
            {'id': 'lucky_wheel', 'name': '幸运转盘', 'emoji': '🎰', 'description': '转盘抽奖，最高x20倍率', 'min_points': 5, 'max_points': 80, 'exclusive': True},
            {'id': 'memory_cards', 'name': '记忆翻牌', 'emoji': '🃏', 'description': '翻牌配对，步数越少分越高', 'min_points': 8, 'max_points': 60, 'exclusive': True}
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


game_manager = None


def init_game_manager(users_data, save_users_func, add_points_func, get_user_data_func):
    global game_manager
    game_manager = GameManager(users_data, save_users_func, add_points_func, get_user_data_func)
    return game_manager


def get_game_manager():
    return game_manager