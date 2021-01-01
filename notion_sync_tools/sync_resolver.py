from dataclasses import dataclass
from enum import Enum
from typing import List

from notion_sync_tools.sync_tree import SyncNode


class SyncActionType(Enum):
    FETCH = 'FETCH'
    DELETE = 'DELETE'


class SyncActionTarget(Enum):
    NOTION = 'NOTION'
    LOCAL = 'LOCAL'


@dataclass
class SyncAction:
    action_type: SyncActionType
    action_target: SyncActionType
    node: SyncNode


# class SyncResolver:
#     def resolve(self, node: SyncNode) -> List[SyncAction]:
#         if node.
