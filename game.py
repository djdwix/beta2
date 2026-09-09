import random
import time
import json
from datetime import datetime

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
            'roulette': self.play_roulette
        }
        self.game_names = {
            'dice': '骰子大战',
            'blackjack': '二十一点',
            'guess_number': '猜数字',
            'rock_paper_scissors': '石头剪刀布',
            'roulette': '轮盘赌'
        }
        self.guess_game_state = {}
        self.rps_game_state = {}

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
            self.save_users()
        stats = user_data['game_stats']
        today = self.get_today()
        if stats.get('today_date') != today:
            stats['today_plays'] = 0
            stats['today_date'] = today
            self.save_users()
        return stats

    def can_play(self, username):
        stats = self.get_user_game_stats(username)
        if not stats:
            return False
        return stats.get('today_plays', 0) < 5

    def get_remaining_plays(self, username):
        stats = self.get_user_game_stats(username)
        if not stats:
            return 0
        return max(0, 5 - stats.get('today_plays', 0))

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

    def calculate_points(self, won, game_type, bet_amount=0, extra_data=None):
        if not won:
            return 0
        base_ranges = {
            'dice': (5, 25),
            'blackjack': (10, 50),
            'guess_number': (8, 35),
            'rock_paper_scissors': (3, 15),
            'roulette': (15, 100)
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
        return random.randint(base_min, base_max)

    def play_dice(self, username, bet_type='high', bet_value=7):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限（5次）', 'remaining': 0}
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
        points = self.calculate_points(won, 'dice', 0, {'diff': diff})
        self.record_play(username, won, points)
        remaining = self.get_remaining_plays(username)
        return {
            'success': True,
            'won': won,
            'player_dice': player_dice,
            'player_total': player_total,
            'ai_dice': ai_dice,
            'ai_total': ai_total,
            'points_earned': points,
            'remaining_plays': remaining,
            'message': '🎉 你赢了！' if won else '😔 你输了！',
            'diff': diff
        }

    def play_blackjack(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限（5次）', 'remaining': 0}
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
        points = self.calculate_points(won, 'blackjack', 0, {'player_total': player_total, 'dealer_total': dealer_total})
        self.record_play(username, won, points)
        remaining = self.get_remaining_plays(username)
        return {
            'success': True,
            'won': won,
            'player_hand': player_hand,
            'player_total': player_total,
            'dealer_hand': dealer_hand,
            'dealer_total': dealer_total,
            'dealer_hit_count': dealer_hit_count,
            'points_earned': points,
            'remaining_plays': remaining,
            'message': '🎉 你赢了！' if won else '😔 你输了！'
        }

    def start_guess_game(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限（5次）', 'remaining': 0}
        secret = random.randint(1, 100)
        self.guess_game_state[username] = {
            'secret': secret,
            'attempts': 0,
            'max_attempts': 7,
            'hints': [],
            'active': True,
            'game_started': True
        }
        return {
            'success': True,
            'max_attempts': 7,
            'message': '🎯 游戏已开始！1-100之间猜一个数字，你有7次机会'
        }

    def guess_number(self, username, guess):
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
            points = self.calculate_points(True, 'guess_number', 0, {'attempts': state['attempts']})
            self.record_play(username, True, points)
            remaining = self.get_remaining_plays(username)
            state['active'] = False
            return {
                'success': True,
                'won': True,
                'secret': secret,
                'attempts': state['attempts'],
                'max_attempts': state['max_attempts'],
                'points_earned': points,
                'remaining_plays': remaining,
                'game_over': True,
                'message': '🎉 你猜对了！数字是 ' + str(secret) + '，用了 ' + str(state['attempts']) + ' 次！'
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
            self.record_play(username, False, 0)
            remaining = self.get_remaining_plays(username)
            return {
                'success': True,
                'won': False,
                'game_over': True,
                'secret': secret,
                'attempts': state['attempts'],
                'max_attempts': state['max_attempts'],
                'points_earned': 0,
                'remaining_plays': remaining,
                'message': '😔 你输了！数字是 ' + str(secret) + '，已用尽所有机会'
            }
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
        if username not in self.guess_game_state:
            return None
        return self.guess_game_state[username]

    def play_guess_number(self, username, guess=None):
        if guess is None:
            return self.start_guess_game(username)
        return self.guess_number(username, guess)

    def reset_guess_game(self, username):
        if username in self.guess_game_state:
            del self.guess_game_state[username]
        return {'success': True, 'message': '游戏已重置'}

    def start_rps_game(self, username):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限（5次）', 'remaining': 0}
        self.rps_game_state[username] = {
            'player_wins': 0,
            'ai_wins': 0,
            'rounds_played': 0,
            'round_history': [],
            'active': True,
            'best_of': 3,
            'game_started': True
        }
        return {
            'success': True,
            'waiting': True,
            'message': '🤖 游戏已开始！请选择出拳：🪨 石头 | 📄 布 | ✂️ 剪刀'
        }

    def rps_choice(self, username, player_move):
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
            points = self.calculate_points(won, 'rock_paper_scissors', 0, {'rounds': state['rounds_played']})
            self.record_play(username, won, points)
            remaining = self.get_remaining_plays(username)
            state['active'] = False
            return {
                'success': True,
                'won': won,
                'player_wins': state['player_wins'],
                'ai_wins': state['ai_wins'],
                'rounds_played': state['rounds_played'],
                'round_history': state['round_history'],
                'best_of': state['best_of'],
                'points_earned': points,
                'remaining_plays': remaining,
                'game_over': True,
                'message': '🎉 你赢了！' if won else '😔 你输了！'
            }
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
        return {'success': True, 'message': '游戏已重置'}

    def get_rps_game_state(self, username):
        if username not in self.rps_game_state:
            return None
        return self.rps_game_state[username]

    def play_roulette(self, username, bet_type='number', bet_value=0):
        if not self.can_play(username):
            return {'success': False, 'error': '今日游戏次数已达上限（5次）', 'remaining': 0}
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
        points = self.calculate_points(won, 'roulette', 0, {'multiplier': multiplier})
        self.record_play(username, won, points)
        remaining = self.get_remaining_plays(username)
        return {
            'success': True,
            'won': won,
            'result': result,
            'color': color,
            'bet_type': bet_type,
            'bet_value': bet_value,
            'multiplier': multiplier,
            'win_desc': win_desc,
            'points_earned': points,
            'remaining_plays': remaining,
            'message': '🎉 你赢了！' + (win_desc if win_desc else '') if won else '😔 你输了！'
        }

    def get_stats(self, username):
        stats = self.get_user_game_stats(username)
        if not stats:
            return {
                'today_plays': 0,
                'max_plays': 5,
                'remaining_plays': 5,
                'total_wins': 0,
                'total_plays': 0,
                'win_rate': 0,
                'today': self.get_today()
            }
        return {
            'today_plays': stats.get('today_plays', 0),
            'max_plays': 5,
            'remaining_plays': max(0, 5 - stats.get('today_plays', 0)),
            'total_wins': stats.get('total_wins', 0),
            'total_plays': stats.get('total_plays', 0),
            'win_rate': round(stats.get('total_wins', 0) / max(1, stats.get('total_plays', 0)) * 100, 1),
            'today': self.get_today()
        }

    def get_game_list(self):
        return [
            {'id': 'dice', 'name': '骰子大战', 'emoji': '🎲', 'description': '掷3个骰子比大小', 'min_points': 5, 'max_points': 40},
            {'id': 'blackjack', 'name': '二十一点', 'emoji': '🃏', 'description': '与庄家比21点', 'min_points': 10, 'max_points': 55},
            {'id': 'guess_number', 'name': '猜数字', 'emoji': '🎯', 'description': '1-100猜数字，7次机会', 'min_points': 8, 'max_points': 45},
            {'id': 'rock_paper_scissors', 'name': '石头剪刀布', 'emoji': '🤖', 'description': '三局两胜', 'min_points': 3, 'max_points': 25},
            {'id': 'roulette', 'name': '轮盘赌', 'emoji': '🎡', 'description': '猜数字/颜色/奇偶', 'min_points': 8, 'max_points': 100}
        ]


game_manager = None

def init_game_manager(users_data, save_users_func, add_points_func, get_user_data_func):
    global game_manager
    game_manager = GameManager(users_data, save_users_func, add_points_func, get_user_data_func)
    return game_manager

def get_game_manager():
    return game_manager