import discord
import random
from enum import Enum
from random import shuffle
from discord.ext import tasks
from itertools import cycle

status = cycle(["[/도움말] 명령어를 입력하여 사용 방법을 확인하세요!"])

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

class GameState(Enum):
    WAITING = 0
    JOINING = 1
    PLAYING = 2

class Player:
    def __init__(self, user):
        self.user = user
        self.balance = 10000
        self.hand = []
        self.folded = False
        self.eliminated = False

game_state = GameState.WAITING
max_players = 0
players = []
current_player = 0
betting_pool = 0

def calculate_hand_value(hand):
    card1, card2 = hand
    special_cases = {
        (3, 8): "38광땡",
        (1, 3): "13광땡",
        (1, 8): "18광땡",
        (1, 2): "알리",
        (1, 4): "독사",
        (1, 9): "구삥",
        (1, 10): "장삥",
        (4, 10): "장사",
        (4, 6): "세륙",
    }
    value = special_cases.get(tuple(sorted(hand)))
    if value:
        return value

    if card1 == card2:
        return f"{card1}땡"

    total = card1 + card2
    if total < 10:
        return f"{total}끗"
    elif total == 10:
        return "망통"
    else:
        return f"{total - 10}끗"

def compare_hands(hand1, hand2):
    hand_values = [
        "망통",
        *["{}끗".format(i) for i in range(1, 10)],
        "세륙",
        "장사",
        "장삥",
        "구삥",
        "독사",
        "알리",
        *["{}땡".format(i) for i in range(1, 10)],
        "18광땡",
        "13광땡",
        "38광땡",
    ]

    value1 = hand_values.index(calculate_hand_value(hand1))
    value2 = hand_values.index(calculate_hand_value(hand2))
    return value1 - value2

async def reset_game(channel):
    global game_state, max_players, players, current_player, betting_pool

    game_state = GameState.WAITING
    max_players = 0
    players.clear()
    current_player = 0
    betting_pool = 0

    embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
    embed.add_field(name="게임 초기화", value="게임이 초기화되었습니다.", inline=False)
    await channel.send(embed=embed)

def deal_cards():
    global players, deck
    for player in players:
        player.hand = [deck.pop() for _ in range(2)]

async def send_hands():
    for player in players:
        hand_value = calculate_hand_value(player.hand)
        embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
        embed.add_field(name="패 확인", value=f"당신의 패는 {player.hand[0]}, {player.hand[1]}입니다. ({hand_value})", inline=False)
        await player.user.send(embed=embed)

async def start_betting(channel):
    global current_player
    current_player = 0
    embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
    embed.add_field(name="베팅 알림", value=f"플레이어 {current_player + 1}님의 차례입니다. 베팅해주세요. (예: /콜, /하프, /올인, /다이)", inline=False)
    await channel.send(embed=embed)

@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))

@tasks.loop(seconds=5)    # 상태 메세지 출력
async def change_status():
    await client.change_presence(activity=discord.Game(next(status)))

@client.event
async def on_message(message):
    global game_state, max_players, players, current_player, betting_pool
    global deck

    if message.author == client.user:
        return

    if message.content.startswith("/섯다"):
        if game_state != GameState.WAITING:
            embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
            embed.add_field(name="오류 발생", value="이미 게임이 진행중입니다.", inline=False)
            await message.channel.send(embed=embed)
            return

        try:
            max_players = int(message.content.split(" ")[1])
            if 2 <= max_players <= 8:
                game_state = GameState.JOINING
                embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
                embed.add_field(name="게임 생성", value=f"최대 {max_players}명 참가 가능한 섯다 게임이 시작되었습니다.\n[/게임참가] 명령어를 사용하여 참가해주세요.", inline=False)
                await message.channel.send(embed=embed)
            else:
                embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
                embed.add_field(name="오류 발생", value="최대 참가자의 수는 (2-8)사이의 숫자여야 합니다.", inline=False)
                await message.channel.send(embed=embed)
        except ValueError:
            embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
            embed.add_field(name="게임 생성", value="최대 참가자 수를 입력해주세요. (예: /섯다 5)", inline=False)
            await message.channel.send(embed=embed)

    elif message.content.startswith("/게임참가"):
        if game_state != GameState.JOINING:
            embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
            embed.add_field(name="오류 발생", value="지금은 참가할 수 없습니다. /섯다 명령어를 사용하여 게임을 시작해주세요.", inline=False)
            await message.channel.send(embed=embed)
            return

        if len(players) >= max_players:
            embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
            embed.add_field(name="오류 발생", value="이미 참가자 수가 최대입니다.", inline=False)
            await message.channel.send(embed=embed)
            return

        if message.author in [player.user for player in players]:
            embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
            embed.add_field(name="오류 발생", value="이미 참가했습니다.", inline=False)
            await message.channel.send(embed=embed)
            return

        new_player = Player(message.author)
        players.append(new_player)
        embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
        embed.add_field(name="참가 완료", value=f"{message.author.name}님, 플레이어 {len(players)}로 참가하였습니다.", inline=False)
        await message.channel.send(embed=embed)

    elif message.content.startswith("/게임시작"):
        if game_state != GameState.JOINING:
            embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
            embed.add_field(name="오류 발생", value="게임을 시작할 수 없습니다. /섯다 명령어를 사용하여 게임을 시작해주세요.", inline=False)
            await message.channel.send(embed=embed)
            return

        if len(players) < 2:
            embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
            embed.add_field(name="오류 발생", value="최소 2명 이상이 참가해야 게임을 시작할 수 있습니다.", inline=False)
            await message.channel.send(embed=embed)
            return

        game_state = GameState.PLAYING
        embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
        embed.add_field(name="게임 시작", value="게임이 시작되었습니다. 각 플레이어에게 카드를 나눠주고 있습니다...", inline=False)
        await message.channel.send(embed=embed)

        deck = list(range(1, 11)) * 2
        random.shuffle(deck)

        for player in players:
            player.hand = [deck.pop(), deck.pop()]
            hand_value = calculate_hand_value(player.hand)
            embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
            embed.add_field(name="패 확인", value=f"당신의 패는 {player.hand[0]}, {player.hand[1]}입니다. ({hand_value})", inline=False)
            await player.user.send(embed=embed)

        betting_pool = len(players) * 100
        for player in players:
            player.balance -= 100

        await message.channel.send(f"1세트가 시작되었습니다. 베팅 차례: 플레이어{current_player + 1}")

    elif message.content.startswith("/"):
        if game_state != GameState.PLAYING:
            await message.channel.send("지금은 베팅할 수 없습니다.")
            return

        player = players[current_player]

        if message.author != player.user:
            await message.channel.send(f"지금은 플레이어 {current_player + 1}의 차례입니다.")
            return

        if player.folded:
            await message.channel.send("이미 다이한 플레이어입니다.")
            return

        if message.content.startswith("/콜"):
            bet = betting_pool // len(players)
            player.balance -= bet
            betting_pool += bet
            await message.channel.send(f"플레이어 {current_player + 1}님이 콜하셨습니다.\n베팅액: {bet}원\n현재 베팅풀: {betting_pool}원\n남은 금액: {player.balance}원")
        
        elif message.content.startswith("/하프"):
            prev_bet = betting_pool // len(players)
            bet = prev_bet + (betting_pool // 2)
            player.balance -= bet
            betting_pool += bet
            await message.channel.send(f"플레이어 {current_player + 1}님이 하프하셨습니다.\n베팅액: {bet}원\n현재 베팅풀: {betting_pool}원\n남은 금액: {player.balance}원")
        elif message.content.startswith("/올인"):
            bet = player.balance
            player.balance = 0
            betting_pool += bet
            await message.channel.send(f"플레이어 {current_player + 1}님이 올인하셨습니다.\n베팅액: {bet}원\n현재 베팅풀: {betting_pool}원")
        elif message.content.startswith("/다이"):
            player.folded = True
            await message.channel.send(f"플레이어 {current_player + 1}님이 다이하셨습니다.")
        else:
            await message.channel.send("올바른 베팅 명령어를 입력해주세요. (예: /콜, /하프, /올인, /다이)")
            return

        current_player = (current_player + 1) % len(players)

        if current_player == 0:
            non_folded_players = [p for p in players if not p.folded]
            if len(non_folded_players) == 1:
                best_player = non_folded_players[0]
            else:
                if len(non_folded_players) > 1:
                    best_player = non_folded_players[0]
                    for p in non_folded_players[1:]:
                        if compare_hands(best_player.hand, p.hand) < 0:
                            best_player = p

            best_player.balance += betting_pool
            betting_pool = 0

            hand_values = [calculate_hand_value(p.hand) for p in players]
            hand_values_str = "\n".join(f"플레이어{i + 1} : {hv}" for i, hv in enumerate(hand_values))
            await message.channel.send(f"{hand_values_str}")
            await message.channel.send(f"승리자 : 플레이어{players.index(best_player) + 1}")

            balances_str = "\n".join(f"플레이어 {i + 1} : {p.balance}원" for i, p in enumerate(players))
            embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
            embed.add_field(name="잔고 확인", value=f"{balances_str}", inline=False)
            await message.channel.send(embed=embed)

            if sum(p.balance < 100 for p in players) >= len(players) -1:
                embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
                embed.add_field(name="세트 종료", value="모든 세트가 종료되었습니다.", inline=False)
                await message.channel.send(embed=embed)
                await reset_game(message.channel)
            else:
                for p in players:
                    p.folded = False
                embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
                embed.add_field(name="게임 시작", value="다음 세트를 시작합니다. 각 플레이어에게 카드를 나눠주고 있습니다...", inline=False)
                await message.channel.send(embed=embed)
                shuffle(deck)
                deal_cards()
                await send_hands()
                await start_betting(message.channel)
                betting_pool = len(players) * 100
                for player in players:
                    player.balance -= 100
                
        else:
            embed = discord.Embed(title="[봇] 섯다게임", color=0x00aaaa)
            embed.add_field(name="베팅 알림", value=f"플레이어{current_player + 1}님의 차례입니다. 베팅해주세요.\n[/콜, /하프, /올인, /다이]", inline=False)
            await message.channel.send(embed=embed)

client.run('MTA5MDY0MDUzMjEyMTg2NjM0MQ.GqBXBH.6bgkNjCXRQvxN0gpE24Zcf0HrngtBnEJcFje1I')