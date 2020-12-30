import fnmatch
import itertools
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Union, List, Dict, Tuple, Pattern, AnyStr, Set

import yaml

from notion_sync_tools.utils.serialization import SecretYamlObject

SyncNodeType = str
SyncNodeRole = str
GUID = str
Path = str
TREE_FILENAME = '.sync.yml'


@dataclass
class SyncMetadataNotion(yaml.YAMLObject):
    yaml_tag = u'!SyncMetadataNotion'
    id: GUID
    synced_at: datetime = field(default_factory=lambda: datetime.now().replace(year=1990))
    deleted: bool = False
    relations: Dict[SyncNodeRole, List[GUID]] = field(default_factory=lambda: {})


@dataclass
class SyncMetadataLocal(yaml.YAMLObject):
    yaml_tag = u'!SyncMetadataLocal'
    path: Path
    synced_at: datetime = field(default_factory=lambda: datetime.now().replace(year=1990))
    deleted: bool = False


@dataclass
class SyncNode(SecretYamlObject):
    hidden_fields = ["parent"]
    yaml_tag = u'!SyncNode'

    parent: Optional[Union['SyncNode', 'SyncTree']] = None
    children: List['SyncNode'] = field(default_factory=lambda: [])
    node_type: SyncNodeType = ''
    node_role: Optional[SyncNodeRole] = None
    metadata_notion: Optional[SyncMetadataNotion] = None
    metadata_local: Optional[SyncMetadataLocal] = None


@dataclass
class SyncTree(SyncNode):
    hidden_fields = ["parent"]
    yaml_tag = u'!SyncTree'

    notion_synced_at: Optional[datetime] = None
    local_synced_at: Optional[datetime] = None

    @staticmethod
    def create_local() -> 'SyncTree':
        return SyncTree(
            node_type='root',
            metadata_local=SyncMetadataLocal(''),
        )

    @staticmethod
    def create_notion(root_id: GUID) -> 'SyncTree':
        return SyncTree(
            node_type='root',
            metadata_notion=SyncMetadataNotion(root_id)
        )

    def write(self, root_path: Path):
        path = os.path.join(root_path, TREE_FILENAME)
        logging.debug(f'Flushing SyncTree to: {path}')
        with open(path, 'w') as f:
            yaml.dump(self, f, default_flow_style=False)

    @staticmethod
    def read(root_path: Path):
        path = os.path.join(root_path, TREE_FILENAME)
        logging.debug(f'Loading SyncTree from: {path}')
        with open(path, 'r') as f:
            return yaml.load(f, Loader=yaml.Loader)

    def flatten(self) -> List[SyncNode]:
        def flatten_node(node: SyncNode):
            return [node, *itertools.chain(*[flatten_node(c) for c in node.children])]
        return flatten_node(self)




REGEX = str


class Mapping:
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
