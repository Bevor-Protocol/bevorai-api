from app.utils.enums import AuditTypeEnum, IntermediateResponseEnum

from .gas import OutputStructure as GasOutputStructure
from .gas import candidate_prompt as gas_candidate
from .gas import reporter_prompt as gas_reporter
from .gas import reviewer_prompt as gas_reviewer
from .security import OutputStructure as SecOutputStructure
from .security import candidate_prompt as sec_candidate
from .security import reporter_prompt as sec_reporter
from .security import reviewer_prompt as sec_reviewer

prompts = {
    AuditTypeEnum.GAS: {
        IntermediateResponseEnum.CANDIDATE: gas_candidate,
        IntermediateResponseEnum.REVIEWER: gas_reviewer,
        IntermediateResponseEnum.REPORTER: gas_reporter,
    },
    AuditTypeEnum.SECURITY: {
        IntermediateResponseEnum.CANDIDATE: sec_candidate,
        IntermediateResponseEnum.REVIEWER: sec_reviewer,
        IntermediateResponseEnum.REPORTER: sec_reporter,
    },
}

formatters = {
    AuditTypeEnum.SECURITY: SecOutputStructure,
    AuditTypeEnum.GAS: GasOutputStructure,
}


__all__ = ["prompts", "formatters"]
