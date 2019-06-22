from game import *
import sys

a = Game(6)

def checkHook(game, action, player, body):
    print("action: {}, player: {}, body: {} \n".format(action, player, body))

a.setPlayer(0, 500, checkHook)
a.setPlayer(1, 500)
a.setPlayer(2, 500)

a.setReady(0)
a.setReady(1)
a.setReady(2)

a.start()

a.pbet(0, 20)
a.pcall(1)
a.pallin(2)

a.pcall(0)
a.pcall(1)

a.pbet(0, 20)
a.pcall(1)

a.pbet(0, 20)
a.pcall(1)
print('end')
sys.exit()