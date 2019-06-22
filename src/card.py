from enum import Enum
class Color(Enum):
    SPADE = 0
    HEART = 1
    CLUB = 2
    DIAMOD = 3

class Card(object):
    def __init__(self, color, num):
        self.color = color
        self.num = num
    
    def __repr__(self):
        return 'color: {}, num: {}'.format(self.color, self.num)
    def __str__(self):
        return 'color: {}, num: {}'.format(self.color, self.num)


