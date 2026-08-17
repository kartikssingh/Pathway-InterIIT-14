import numpy as np

def compute_evidence(rule_hits, lr_dict, pi):
    O0 = pi / (1 - pi + 1e-9)
    LR_product = 1.0
    for rule_name, hit in rule_hits.items():
        if hit == 1:
            LR_product *= lr_dict.get(rule_name, 1.0)
    posterior = (O0 * LR_product) / (1 + O0 * LR_product)

    return posterior

