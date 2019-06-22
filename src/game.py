from enum import Enum
from functools import wraps
from card import *
import threading
import random

class GameStatus(Enum):
    WAITFORPLAYERREADY = 1
    RUNNING = 2
    CONTINUING = 3

class RoundStatus(Enum):
    PREFLOP = 1
    FLOP = 2
    TURN = 3
    RIVER = 4
    END = 5

def emptyHook(*args, **kwargs):
    return 0

def critical(func):
    def wrapper(self, *args, **kwargs):
        self.lock.acquire()
        ret = func(self, *args, **kwargs)
        self.lock.release()
        return ret
    return wrapper

def status(ss):
    def dec(func):
        def wrapper(self, *args, **kwargs):
            for s in ss:
                if self.gameStatus == s:
                    return func(self, *args, **kwargs)
            return -1
        return wrapper
    return dec

class Game(object):
    def __init__(self, maxPlayer):
        assert maxPlayer > 1
        self.maxPlayer = maxPlayer
        self.players = [Player() for i in range(maxPlayer)]
        self.gameStatus = GameStatus.WAITFORPLAYERREADY
        self.lock = threading.RLock()
        self.numOfPlayer = 0
        self.deck = Deck()
        self.timer = threading.Timer(15, self.timeFunc)
        self.btn = -1
        self.ante = 20

    def timeFunc(self):
        task = threading.Thread(target=self.pfold, args=(self.exePos))
        task.start()

    @critical
    @status([GameStatus.WAITFORPLAYERREADY])
    def setPlayer(self, pos, chip, hook = emptyHook):
        player = self.players[pos]
        # is occupied ?
        if player.active:
            return -1

        player.active = True
        player.chip = chip
        player.hook = hook
        self.numOfPlayer = self.numOfPlayer + 1
        self.notifyAll('JOIN', pos, {chip: player.chip})
        return 0

    @critical
    @status([GameStatus.WAITFORPLAYERREADY])
    def setReady(self, pos):
        player = self.players[pos]
        
        if player.active:
            player.ready = True
            self.notifyAll('READY', pos, {})
            return 0
        return -1

    @critical
    @status([GameStatus.WAITFORPLAYERREADY])
    def start(self):
        for i in range(0, self.maxPlayer):
            if (self.players[i].active != self.players[i].ready):
                return -1
        # all the players are ready
        self.gameStatus = GameStatus.RUNNING
        self.roundStatus = RoundStatus.PREFLOP
        
        def sendCardsToPlayer(player):
            player.cards[0] = self.deck.getCard()
            player.cards[1] = self.deck.getCard()
            return {'cards': player.cards}
        
        # set array and send different msg to players repectively
        self.notifyAll('PREFLOP', -1, list(map(sendCardsToPlayer, self.players)), True)

        # blind
        self.btn = self.findNextActivePlayer(self.btn)
        self.sb = self.findNextActivePlayer(self.btn)
        self.bb = self.findNextActivePlayer(self.sb)
        self.utg = self.findNextActivePlayer(self.bb)

        # a flag for end of one round
        self.exePos = self.utg
        self.nextRound = self.utg

        self.putChip(self.sb, self.ante / 2, 'SB')
        self.putChip(self.bb, self.ante, 'BB')

        self.notifyAll('START', -1, {'btn': self.btn, 'sb': self.sb, 'bb': self.bb, 'utg': self.utg})
        return 0

    def findNextActivePlayer(self, pos):
        pos = pos + 1
        count = 0
        while(self.players[pos].active == False or self.players[pos].fold or self.players[pos].allin):
            pos = (pos + 1) % self.maxPlayer
            count = count + 1

            # nobody can do action
            if (count > self.maxPlayer):
                return -1
        return pos

    def invokeNextPlayer(self):
        self.timer.cancel()
        
        r = self.findNextActivePlayer(self.exePos)
        if r == -1:
            self.gend()
        else:
            self.exePos = r

        # touch the bound
        if (self.exePos == self.nextRound):
            if self.roundStatus == RoundStatus.PREFLOP:
                self.flop()
                self.roundStatus = RoundStatus.FLOP
            elif self.roundStatus == RoundStatus.FLOP:
                self.turn()
                self.roundStatus = RoundStatus.TURN
            elif self.roundStatus == RoundStatus.TURN:
                self.river()
                self.roundStatus = RoundStatus.RIVER
            elif self.roundStatus == RoundStatus.RIVER:
                self.end()
                self.roundStatus = RoundStatus.END

        self.timer = threading.Timer(15, self.timeFunc)
        self.timer.start()

    def gend(self):
        # continue round until end
        self.roundStatus = self.roundStatus + 1
        if self.roundStatus == RoundStatus.FLOP:
            self.flop()
            self.roundStatus = self.roundStatus + 1
        if self.roundStatus == RoundStatus.TURN:
            self.turn()
            self.roundStatus = self.roundStatus + 1
        if self.roundStatus == RoundStatus.RIVER:
            self.river()
            self.roundStatus = self.roundStatus + 1
        if self.roundStatus == RoundStatus.END:
            self.end()

    def flop(self):
        self.pubCards = [self.deck.getCard() for i in range(3)]
        self.notifyAll('FLOP', -1, {'pubCards': self.pubCards})

    def turn(self):
        self.pubCards.append(self.deck.getCard())
        self.notifyAll('TURN', -1, {'pubCards': self.pubCards})

    def river(self):
        self.pubCards.append(self.deck.getCard())
        self.notifyAll('TURN', -1, {'pubCards': self.pubCards})

    def end(self):
        # how to do?
        # self.notifyAll('TURN', -1, {pubCards: self.pubCards})
        pass

    def notifyAll(self, action, player, body, isArray = False):
        for p in range(0, self.maxPlayer):
            if self.players[p].active == False:
                continue
            
            print("x")
            if (isArray):
                msg = body[p]
            else:
                msg = body
            # task = threading.Thread(target=p.hook, args=(action,player,msg))
            # task.start()
            self.players[p].hook(action, player, msg)

    def putChip(self, pos, num, action):
        player = self.players[pos]
        player.chip = player.chip - num
        player.chipBet = player.chipBet + num
        self.notifyAll(action, pos, {'num': int(num)})
    
    @critical
    @status([GameStatus.RUNNING])
    def pbet(self, pos, num):
        if (pos != self.exePos):
            return -1
        
        self.putChip(pos, num, 'BET')
        self.lastBet = num
        self.permitCheck = True
        self.invokeNextPlayer()
        return 0

    @critical
    @status([GameStatus.RUNNING])
    def pcall(self, pos):
        if (pos != self.exePos):
            return -1
        num = self.lastBet
        self.putChip(pos, num, 'CALL')
        self.invokeNextPlayer()
        return 0

    @critical
    @status([GameStatus.RUNNING])
    def pfold(self, pos):
        if (pos != self.exePos):
            return -1
        self.players[pos].fold = TRUE
        self.notifyAll('FOLD', pos, {})
        self.invokeNextPlayer()
        return 0

    @critical
    @status([GameStatus.RUNNING])
    def pcheck(self, pos):
        if (pos != self.exePos or self.permitCheck == False):
            return -1

        self.notifyAll('CHECK', pos, {})
        self.invokeNextPlayer()
        return 0

    @critical
    @status([GameStatus.RUNNING])
    def praise(self, pos, num):
        if (pos != self.exePos or num < self.lastBet * 2):
            return -1
        
        self.lastBet = num
        self.permitCheck = False
        self.putChip(pos, num, 'RAISE')
        self.invokeNextPlayer()
        return 0

    @critical
    @status([GameStatus.RUNNING])
    def pallin(self, pos):
        if (pos != self.exePos):
            return -1
        
        self.players[pos].allin = True
        self.putChip(pos, self.players[pos].chip, 'ALLIN')
        self.invokeNextPlayer()
        return 0

class Player(object):
    def __init__(self):
        self.chip = 0
        self.chipBet = 0
        self.cards = [0] * 5
        self.active = False  # join a game
        self.ready = False 
        self.fold = False
        self.allin = False

        # intend to support differenct interaction like AI, websocket
        self.hook = emptyHook

class Deck(object):
    def __init__(self):
        self.deckCards = list(range(0, 52))
        self.shuffle()

    def getCard(self):
        num = self.deckCards[self.i]
        card = Card(int(num / 13), num % 13)
        self.i = self.i + 1
        return card

    def shuffle(self):
        random.shuffle(self.deckCards)
        self.i = 0