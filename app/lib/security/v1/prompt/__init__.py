from app.utils.types.shared import Candidates

from .candidate import candidates
from .reviewer.base import prompt

prompts = Candidates(candidates=candidates, reviewer=prompt)
