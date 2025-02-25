import math


class Usage:
    INPUT_COST = 0.15
    OUTPUT_COST = 0.6
    BASE_FACTOR = 1_000_000
    PRICE_PEG = 0.001
    MULTIPLIER = 4

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
        credit_cost = token_value * self.MULTIPLIER

        floor_cost = round(0.1 / self.PRICE_PEG)

        return max(floor_cost, math.ceil(credit_cost))

    @classmethod
    def estimate_pricing(self):
        standard_output = 5_000  # historically what we've seen per audit
        standard_input = 22_000  # historically, given an ERC-20 input

        compute_cost = (
            standard_input * self.INPUT_COST + standard_output * self.OUTPUT_COST
        )
        base_compute = compute_cost / self.BASE_FACTOR

        token_value = base_compute / self.PRICE_PEG
        credit_cost = token_value * self.MULTIPLIER

        floor_cost = round(0.1 / self.PRICE_PEG)

        return max(floor_cost, math.ceil(credit_cost))
