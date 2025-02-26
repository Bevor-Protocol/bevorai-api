import math


class Usage:
    INPUT_COST = 0.15  # cost per X input token
    OUTPUT_COST = 0.6  # cost per X output token
    BASE_FACTOR = 1_000_000  # number of tokens for pricing
    PRICE_PEG = 0.001  # token price peg
    PREMIUM = 4  # premium factor on top of compute

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0

    def add_input(self, n: int):
        self.input_tokens += n

    def add_output(self, n: int):
        self.output_tokens += n

    def get_cost(self):
        compute_cost = (
            self.input_tokens * self.INPUT_COST + self.output_tokens * self.OUTPUT_COST
        )
        base_compute = compute_cost / self.BASE_FACTOR

        token_value = base_compute / self.PRICE_PEG
        credit_cost = token_value * self.PREMIUM

        floor_cost = round(0.1 / self.PRICE_PEG)

        return max(floor_cost, math.ceil(credit_cost))

    @classmethod
    def estimate_pricing(self):
        standard_output_tokens = 5_000  # historically what we've seen per audit
        standard_input_tokens = 22_000  # historically, given an ERC-20 input

        compute_cost = (
            standard_input_tokens * self.INPUT_COST
            + standard_output_tokens * self.OUTPUT_COST
        )
        base_compute = compute_cost / self.BASE_FACTOR

        token_value = base_compute / self.PRICE_PEG
        credit_cost = token_value * self.PREMIUM

        floor_cost = round(0.1 / self.PRICE_PEG)

        return max(floor_cost, math.ceil(credit_cost))


class StaticAnalysis:
    PRICE_PEG = 0.001
    PREMIUM = 1

    def get_cost(self):
        # TODO come back to this, peg it to 1 credit for now.
        return 1

    @classmethod
    def estimate_pricing(self):
        return 1
