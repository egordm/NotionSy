import fnmatch
import itertools
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Union, List, Dict, Tuple, Pattern, AnyStr, Set, Callable
from uuid import UUID

import yaml

from notion_sync_tools.utils.serialization import SecretYamlObject

SyncNodeRole = str
GUID = str
Path = str
TREE_FILENAME = '.sync.yml'


class SyncNodeType(Enum):
    ROOT = 'ROOT'
    NOTE = 'NOTE'
    GROUP = 'GROUP'
    UNKNOWN = 'UNKNOWN'

    def __str__(self):
        return self.value


def enum_representer(tag: str):
    def rep(dumper, data):
        return dumper.represent_scalar(tag, str(data.value))
    return rep


def enum_deserailize(enum):
    def rep(loader, node):
        return enum(node.value)
    return rep


yaml.add_representer(SyncNodeType, enum_representer('!SyncNodeType'))
yaml.add_constructor('!SyncNodeType', enum_deserailize(SyncNodeType))


@dataclass
class SyncMetadataNotion(yaml.YAMLObject):
    """
    Struct responsible for storing the required metadata for notion provider
    """
    yaml_tag = u'!SyncMetadataNotion'
    id: GUID
    title: str
    updated_at: datetime = field(default_factory=lambda: datetime.now().replace(year=1990))
    deleted: bool = False
    relations: Dict[SyncNodeRole, List[GUID]] = field(default_factory=lambda: {})

    def __str__(self) -> str:
        return f'{self.title}\n\t{self.updated_at.strftime("%Y-%m-%d %H:%M")}|{self.deleted}'


@dataclass
class SyncMetadataLocal(yaml.YAMLObject):
    """
    Struct responsible for storing the required metadata for local provider
    """
    yaml_tag = u'!SyncMetadataLocal'
    path: Path
    updated_at: datetime = field(default_factory=lambda: datetime.now().replace(year=1990))
    deleted: bool = False

    def __str__(self) -> str:
        return f'{self.path}\n\t{self.updated_at.strftime("%Y-%m-%d %H:%M")}|{self.deleted}'


SyncMetadata = Union[SyncMetadataNotion, SyncMetadataLocal]


@dataclass
class SyncNode(SecretYamlObject):
    """
    General node struct toring data about a sync node which may be a directory/group or a file
    """
    hidden_fields = ["parent"]
    yaml_tag = u'!SyncNode'

    id: UUID = field(default_factory=lambda: uuid.uuid4())
    parent: Optional[Union['SyncNode', 'SyncTree']] = None
    children: List['SyncNode'] = field(default_factory=lambda: [])
    node_type: SyncNodeType = field(default_factory=lambda: SyncNodeType.UNKNOWN)
    node_role: Optional[SyncNodeRole] = None
    metadata_notion: Optional[SyncMetadataNotion] = None
    metadata_local: Optional[SyncMetadataLocal] = None
    synced_at: Optional[datetime] = None

    def copy_metadata_from(self, node: 'SyncNode'):
        """
        Copies all provider based metadata from the given node to the current node
        :param node:
        :return:
        """
        self.id = node.id
        self.metadata_local = node.metadata_local
        self.metadata_notion = node.metadata_notion
        self.node_role = node.node_role
        self.synced_at = node.synced_at

    def clone_childless(self, parent: 'SyncNode'):
        """
        Clones all provider based data into a new node
        :param parent:
        :return:
        """
        res = SyncNode(
            parent=parent,
            node_type=self.node_type
        )
        res.copy_metadata_from(self)
        return res

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
        :param recursive:
        :param notion:
        :param local:
        :return:
        """
        # Check children dates first
        if recursive:
            for c in self.children:
                c.collect_updated_at(notion, local, recursive)

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

    def changed(self) -> Tuple[bool, bool]:
        return (
            (not self.metadata_notion or not self.synced_at or self.metadata_local.updated_at > self.synced_at)
            if self.metadata_local else False,
            (not self.metadata_local or not self.synced_at or self.metadata_notion.updated_at > self.synced_at)
            if self.metadata_notion else False
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
            node_type=SyncNodeType.ROOT,
            metadata_local=SyncMetadataLocal(''),
        )

    @staticmethod
    def create_notion(root_id: GUID) -> 'SyncTree':
        return SyncTree(
            node_type=SyncNodeType.ROOT,
            metadata_notion=SyncMetadataNotion(root_id, '')
        )


@dataclass
class SyncData(SecretYamlObject):
    """
    Data object storing all the necessary data for sync
    """
    hidden_fields = []
    yaml_tag = u'!SyncData'

    notion_tree: SyncTree
    local_tree: SyncTree

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
