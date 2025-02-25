from .v1 import structure as v1_structure

CURRENT_VERSION = "v1"

versions = {"v1": v1_structure}

structure = versions[CURRENT_VERSION]
