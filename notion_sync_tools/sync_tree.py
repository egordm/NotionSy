import fnmatch
import itertools
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Union, List, Dict, Tuple, Pattern, AnyStr, Set, Callable

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
    title: str
    updated_at: datetime = field(default_factory=lambda: datetime.now().replace(year=1990))
    deleted: bool = False
    relations: Dict[SyncNodeRole, List[GUID]] = field(default_factory=lambda: {})


@dataclass
class SyncMetadataLocal(yaml.YAMLObject):
    yaml_tag = u'!SyncMetadataLocal'
    path: Path
    updated_at: datetime = field(default_factory=lambda: datetime.now().replace(year=1990))
    deleted: bool = False

SyncMetadata = Union[SyncMetadataNotion, SyncMetadataLocal]

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

    @property
    def unique_id(self):
        return (self.metadata_notion.id if self.metadata_notion else '') + \
         (self.metadata_local.path if self.metadata_local else '')

    def flatten(self, filter_fn: Callable[['SyncNode'], bool] = None) -> List['SyncNode']:
        """
        Flattens the node tree into one single list. Uses given filter to exclude nodes to the final list
        :param filter_fn:
        :return:
        """
        if filter_fn is None:
            filter_fn = lambda x: True

        def flatten_node(node: SyncNode):
            children = itertools.chain(*[flatten_node(c) for c in node.children])
            return [node, *children] if filter_fn(node) else list(children)

        return flatten_node(self)

    def collect_updated_at(self, notion=False, local=False, recursive=False):
        """
        Updates updated_at according to it's children
        :param notion:
        :param local:
        :return:
        """
        # Check children dates first
        if recursive:
            for child in self.children:
                child.collect_updated_at(notion, local, recursive)

        def collect_notion(child: SyncNode):
            return child.metadata_notion.updated_at if child.metadata_notion else datetime.now().replace(year=1990)

        def collect_local(child: SyncNode):
            return child.metadata_local.updated_at if child.metadata_local else datetime.now().replace(year=1990)

        if notion:
            self.metadata_notion.updated_at = max(
                self.metadata_notion.updated_at,
                self.metadata_notion.updated_at,
                *map(collect_notion, self.children)
            )
        if local:
            self.metadata_local.updated_at = max(
                self.metadata_local.updated_at,
                self.metadata_local.updated_at,
                *map(collect_local, self.children)
            )



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
            metadata_notion=SyncMetadataNotion(root_id, '')
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
