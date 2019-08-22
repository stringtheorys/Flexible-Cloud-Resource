"""Optimality Testing"""

from __future__ import annotations

import json
from tqdm import tqdm

from core.model import reset_model, ModelDist, load_dist

from auction.vcg import vcg_auction
from auction.iterative_auction import iterative_auction


def auction_price(model_dist, name, repeats=50):
    """Auction price testing"""
    epsilons = (1, 2, 3, 5, 7, 10)

    data = []

    for _ in tqdm(range(repeats)):
        jobs, servers = model_dist.create()
        results = {}

        vcg_result = vcg_auction(jobs, servers, 15)
        if vcg_result is None:
            print("VCG result fail")
            continue
        results['vcg'] = (vcg_result.total_utility, vcg_result.total_price)
        reset_model(jobs, servers)

        for epsilon in epsilons:
            iterative_result = iterative_auction(jobs, servers)
            if iterative_result is None:
                print("Iterative result fail")
                continue

            iterative_prices, iterative_utilities = iterative_result
            results['iterative ' + str(epsilon)] = (iterative_utilities[-1], iterative_prices[-1])
            reset_model(jobs, servers)

        # print(results)
        data.append(results)

    with open('auction_results_{}.txt'.format(name), 'w') as outfile:
        json.dump(data, outfile)
    print("Model {} results".format(name))
    print(data)


if __name__ == "__main__":
    print("Auction Test")
    model_name, job_dist, server_dist = load_dist('models/basic.model')
    for num_jobs, num_servers in ((12, 2), (15, 3), (25, 5), (100, 20), (150, 25)):
        model_dist = ModelDist(model_name, job_dist, num_jobs, server_dist, num_servers)
        auction_price(model_dist, 'Job {} server {}'.format(num_jobs, num_servers))
