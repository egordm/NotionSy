import fnmatch
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union, List, Dict, Tuple, Pattern, AnyStr

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
    synced_at: datetime
    deleted: bool


@dataclass
class SyncMetadataLocal(yaml.YAMLObject):
    yaml_tag = u'!SyncMetadataLocal'
    path: Path
    synced_at: datetime
    deleted: bool


@dataclass
class SyncNode(SecretYamlObject):
    hidden_fields = ["parent"]
    yaml_tag = u'!SyncNode'

    parent: Optional[Union['SyncNode', 'SyncTree']]
    children: List['SyncNode']
    node_type: SyncNodeType
    node_role: Optional[SyncNodeRole]
    metadata_notion: Optional[SyncMetadataNotion]
    metadata_local: Optional[SyncMetadataLocal]


@dataclass
class SyncTree(SyncNode):
    hidden_fields = ["parent"]
    yaml_tag = u'!SyncTree'

    notion_synced_at: Optional[datetime]
    local_synced_at: Optional[datetime]

    @staticmethod
    def create_local() -> 'SyncTree':
        return SyncTree(
            None, [],
            'root',
            None,
            None,
            SyncMetadataLocal('', datetime.now(), False),
            None,
            None
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


GLOB = str


class Mapping:
    mapping: Dict[GLOB, SyncNodeRole]
    baked_mapping: List[Tuple[Pattern[AnyStr], SyncNodeRole]]

    def __init__(self, mapping: Dict[GLOB, SyncNodeRole]) -> None:
        super().__init__()
        self.mapping = mapping
        self.baked_mapping = [
            (re.compile(fnmatch.translate(k)), v) for (k, v) in mapping.items()
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
