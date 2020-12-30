import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union, List

import yaml

from notion_sync_tools.utils.serialization import SecretYamlObject

SyncNodeType = str
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
