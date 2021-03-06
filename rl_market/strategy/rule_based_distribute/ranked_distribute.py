from ..base import Strategy
import numpy as np

"""
try rank each seller and distribute fix amount view
"""
class RankedDistribute(Strategy):
    def __init__(self):
        pass

    def __repr__(self):
        return "Ranked Distribute"

    def reset(self):
        pass

    def play(self, game):
        state = game.get_observation()
        #(t, 4, nr_seller)
        view = state[-1][0]
        trade_amount = state[-1][1]
        trade_value = state[-1][2]
        trade_price = state[-1][3]

        array = -np.array(trade_value)
        order = array.argsort()
        ranks = order.argsort()
        weight = np.exp(-ranks)
        return weight

