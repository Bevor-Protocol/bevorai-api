from .access_control import prompt as access_control_prompt
from .control_flow import prompt as control_flow_prompt
from .data_handling import prompt as data_handling_prompt
from .economic import prompt as economic_prompt
from .logic import prompt as logic_prompt
from .math import prompt as math_prompt

candidates = {
    "access_control": access_control_prompt,
    "control_flow": control_flow_prompt,
    "data_handling": data_handling_prompt,
    "economic": economic_prompt,
    "logic": logic_prompt,
    "math": math_prompt,
}
