import re
from dataclasses import field, dataclass
from enum import Enum
from typing import Dict, List, Tuple, Pattern, AnyStr, Optional, Set

from notionsy.sync_planner import SyncAction
from notionsy.sync_tree import SyncNodeRole, SyncNode, Path, SyncNodeType, GUID, SyncData, SyncTree

REGEX = str


class Mapping:
    """
    Struct storing the data to map the sync object to their roles based on the provider
    """
    mapping: Dict[REGEX, SyncNodeRole]
    baked_mapping: List[Tuple[Pattern[AnyStr], SyncNodeRole]]

    def __init__(self, mapping: Dict[REGEX, SyncNodeRole]) -> None:
        super().__init__()
        self.mapping = mapping
        self.baked_mapping = [
            (re.compile(k), v) for (k, v) in mapping.items()
        ]

    def match(self, path: str) -> Optional[SyncNodeRole]:
        """
        Matches given path with specified role mapping
        :param path:
        :return:
        """
        for (rep, role) in self.baked_mapping:
            if rep.match(path):
                return role
        return None

    def roles(self) -> Set[SyncNodeRole]:
        return set(self.mapping.values())


class ResourceAction(Enum):
    CREATE = 'create'
    UPDATE = 'update'


@dataclass
class NotionResourceMapper:
    """
    Mapper with action_resource functions to create the objects in notion accordign to a custom mapping
    """
    content_mapping: Dict[SyncNodeRole, SyncNode]

    def execute(self, resource_action: ResourceAction, resource: SyncNodeRole, action: SyncAction):
        method = getattr(self, f'{resource_action.value}_{resource}', None)
        if method is None:
            raise Exception(f'Notion Resource Mapper is missing: {resource_action.value}_{resource}')
        return method(action)


@dataclass
class SyncConfig:
    root_dir: Path
    notion_root: GUID
    local_mapping: Mapping
    notion_mapping: Mapping
    structure_types: Dict[SyncNodeRole, SyncNodeType]
    hierarchy: List[str]
    resource_mapper: NotionResourceMapper

    def data(self) -> SyncData:
        return SyncData(
            SyncTree.create_notion(self.notion_root),
            SyncTree.create_local(),
            self.root_dir
        )
