from .base import Seller
from .simple_seller import SimpleSeller
import numpy as np


class TrickySeller(SimpleSeller):
    def __init__(self, trick_prob = 0.1, epsilon_sampler = None, *args, **kargs):
        if epsilon_sampler is not None:
            self.trick_prob = epsilon_sampler.sample()
        else:
            self.trick_prob = trick_prob
        super(TrickySeller, self).__init__(*args, **kargs)

    def __repr__(self):
        return "Tricky Seller"

    def decide_price(self, game, index):
        nr_history = game.duration

        if nr_history <=2:
            return self.price_sampler.sample()

        # trick the direct_algorithm by randomly pick 0.5 price to attract buyers
        if np.random.random()<self.trick_prob:
            return 0.

        # pick up the most profitable index instead

        best_price, best_trade_amount = game.price[-1][index], game.trade_amount[-1][index]
        best_profit = (best_price - self.cost) * best_trade_amount
        self.trade_history.append((best_price, best_profit))

        if len(self.trade_history)> self.max_trade_history:
            self.trade_history=self.trade_history[1:]
        #find the price most successful and sample from that range
        best_price, best_profit = None, 0
        for t, (price, profit) in enumerate(self.trade_history):
            interval = len(self.trade_history) - t
            discounted_profit = profit * np.power(self.discount_factor, interval)
            if discounted_profit > best_profit:
                best_price = price
                best_profit = profit
        if best_price is None:
            return self.price_sampler.sample()
        return self._regularize(best_price + self.noise_sampler.sample())
