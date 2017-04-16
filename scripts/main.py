from rl_market.strategy.ddpg.ddpg import DDPG

from rl_market.strategy.rule_based_distribute.random_distribute import RandomDistribute
from rl_market.strategy.rule_based_distribute.uniform_distribute import UniformDistribute
from rl_market.strategy.rule_based_distribute.direct_optimize import DirectOptimize
from rl_market.strategy.rule_based_distribute.ranked_distribute import RankedDistribute
from rl_market.strategy.rule_based_distribute.accum_optimize import AccumOptimize

from rl_market.strategy.ddpg.model_generator.simple_fc import SimpleFC
from rl_market.strategy.ddpg.model_generator.gru import GRUModel

from rl_market.game.price_market import PriceMarket
from rl_market.player.buyer.simple_buyer import SimpleBuyer
from rl_market.player.buyer.history_buyer import HistoryBuyer
from rl_market.player.seller.comparative_seller import ComparativeSeller
from rl_market.player.seller.tricky_seller import TrickySeller
from rl_market.player.seller.simple_seller import SimpleSeller
from rl_market.player.seller.ddpg_seller import DDPGSeller

import rl_market.utils.logging_conf
import rl_market.utils.sampler as sampler
import logging as log

from tqdm import tqdm
import numpy as np
import argparse

THE_MEANING_OF_LIFE_UNIVERSE_AND_EVERYTHING=42

strategy_map={
    "uniform":UniformDistribute,
    "random":RandomDistribute,
    "direct":DirectOptimize,
    "ranked":RankedDistribute,
    "accum":AccumOptimize,
}

def spec_str(args, name):
    if args.ranked:
        ranked="ranked"
    else:
        ranked="distr"
    return "{}/ddpg_{}_{}_{}_{}_{}_{}_{}.hdf5".format(args.path, name, args.buyer,args.seller, args.nr_seller, args.duration,ranked, args.model)
    return

def noise_func(action):
    return  0.005 * np.random.randn(1)

def sorted_observation_func(observation):
    neg_trade_value = -np.array(observation[-1][2])
    order = neg_trade_value.argsort()
    ranks = order.argsort()
    #print(observation[-1][2])
    #print(ranks)
    sted = np.array([[observation[-1][i][order] for i in range(4)]])
    #print(sted.shape)
    #print(sted[-1][1][ranks]-observation[-1][1])
    return sted, ranks

def sorted_action_func(action_encoding, args):
    #print(action_encoding, args)
    return action_encoding[args]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("s", help= "the strategy to test")
    parser.add_argument("--ranked", action = "store_true")
    parser.add_argument("--duration", type=int, default=1)
    parser.add_argument("--buyer", default="simple")
    parser.add_argument("--seller", default="simple")
    parser.add_argument("--nr_seller", type=int, default=100)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--model", default="fc")
    parser.add_argument("--path", default="../data/")

    parser.add_argument("--sorted",action="store_true")
    parser.add_argument("--pretrain",default="")

    args = parser.parse_args()
    if args.model == "fc":
        model_class = SimpleFC
    elif args.model == "gru":
        model_class = GRUModel
    elif args.s == "ddpg":
        assert(False),"invalid model spec"

    if args.buyer == "simple":
        buyer_class = SimpleBuyer
    elif args.buyer == "history":
        buyer_class = HistoryBuyer
    else:
        assert(False),"invalid buyer type"

    if args.seller == "simple":
        seller_class=SimpleSeller
    elif args.seller == "tricky":
        seller_class=TrickySeller
    elif args.seller == "comp":
        seller_class=ComparativeSeller
    else:
        assert(False),"invalid seller type"

    if args.sorted:
        observation_func=sorted_observation_func
        action_func=sorted_action_func
    else:
        observation_func=None
        action_func=None

    # ================ end of parse args ================

    np.random.seed(THE_MEANING_OF_LIFE_UNIVERSE_AND_EVERYTHING)
    log.info("random seed set as {}".format(THE_MEANING_OF_LIFE_UNIVERSE_AND_EVERYTHING))
    buyer = buyer_class()

    quality_sampler = sampler.BoundGaussianSampler(mu = 0.5, sigma = 0.5/3)
    cost_sampler = sampler.BoundGaussianSampler(mu = 0.5, sigma = 0.5/3)
    #cost_sampler = sampler.UniformSampler()
    price_sampler = sampler.BoundGaussianSampler(mu = 0.5, sigma = 0.5/3)
    noise_sampler = sampler.GaussianSampler(mu = 0., sigma = 0.05/3)

    sellers = [seller_class(quality_sampler=quality_sampler, cost_sampler=cost_sampler, price_sampler=price_sampler, noise_sampler=noise_sampler) for i in range(args.nr_seller)]

    log.info("seller:{}".format(seller_class))
    game = PriceMarket(sellers=sellers,buyer=buyer,nr_observation = args.duration, max_duration=1000)
    log.info("initialize game:{}".format(game))
    log.info("state shape: {}".format(game.state_shape))

    if args.train:
        log.info("start training")
        if args.resume:
            actor_weight_path=spec_str(args, "actor")
            critic_weight_path=spec_str(args, "critic")
        else:
            actor_weight_path=None
            critic_weight_path=None

        strategy = DDPG(state_shape = game.state_shape, action_dim = game.action_dim,
                generator=model_class(),
                observation_func=observation_func,
                action_func=action_func,
                noise_func=noise_func,
                actor_save_path = spec_str(args, "actor"),
                critic_save_path = spec_str(args, "critic"),
                actor_weight_path=actor_weight_path,
                critic_weight_path=critic_weight_path
        )
        if args.pretrain !="":
            log.info("pretrain enabled with strategy {}".format(args.pretrain))
            pretrain_strategy = strategy_map[args.pretrain]()
            strategy.pretrain(game, pretrain_strategy, nr_episode = 1)
        strategy.train(game, nr_episode = 1000, nr_steps = 1000)
        return
    if args.s == "ddpg":
        DDPG(state_shape = game.state_shape, action_dim = game.action_dim,
                generator=model_class(),
                observation_func=observation_func,
                action_func=action_func,
                noise_func=noise_func,
                actor_weight_path=spec_str(args, "actor"),
                critic_weight_path=spec_str(args, "critic")
        )
    else:
        assert(args.s in strategy_map)
        strategy = strategy_map[args.s]()

    log.info("start testing {}".format(strategy))
    for epoch in range(1000):
        total_reward = 0
        game.reset(hard=True)
        strategy.reset()
        pbar = tqdm(range(1000))
        for step in pbar:
            #print("=========step {}=========\n{}\n".format(step,game.get_observation_string()))
            action =  strategy.play(game)
            reward, done = game.step(action)
            total_reward += reward
            pbar.set_description("s{} R{:3}".format(step, reward))
            if done:
                break
        log.info("total reward@{}-th episode: {}".format(epoch, total_reward))

if __name__=="__main__":
    main()
