import itertools
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Union, List, Dict, Tuple, Callable, Iterable
from uuid import UUID

import yaml

from notion_sync_tools.utils.serialization import SecretYamlObject

SyncNodeRole = str
GUID = str
Path = str
TREE_FILENAME = '.sync.yml'
INTERNAL_FILES = [TREE_FILENAME, 'resources']


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
    def rep(_loader, node):
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

    def traverse(self) -> Iterable['SyncNode']:
        yield self
        for c in self.children:
            yield from c.traverse()

    def changed(self) -> Tuple[bool, bool]:
        return (
            (not self.metadata_notion or not self.synced_at or self.synced_at < self.metadata_local.updated_at)
            if self.metadata_local else False,  # Changed local
            (not self.metadata_local or not self.synced_at or self.synced_at < self.metadata_notion.updated_at)
            if self.metadata_notion else False  # Changed notion
        )

    def local_dir(self) -> Path:
        parts = []
        node = self.parent
        while node is not None:
            parts.append(node.metadata_local.path)
            node = node.parent
        if len(parts) == 0:
            return ''
        elif len(parts) == 1:
            return parts[0]
        return os.path.join(*reversed(parts))

    def local_path(self) -> Path:
        return os.path.join(self.local_dir(), self.metadata_local.path)


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

    def read(self, root_path: Path):
        path = os.path.join(root_path, TREE_FILENAME)
        if not os.path.exists(path):
            logging.debug(f'No SyncTree found at: {path}')
            return

        logging.debug(f'Loading SyncTree from: {path}')
        with open(path, 'r') as f:
            data: SyncData = yaml.load(f, Loader=yaml.Loader)
            self.notion_tree = data.notion_tree
            self.local_tree = data.local_tree

        # Fill parent fields which are not serialized
        def propagate_parents(parent: Optional[SyncNode], node: SyncNode):
            node.parent = parent
            for child in node.children:
                propagate_parents(node, child)
        propagate_parents(None, self.notion_tree)
        propagate_parents(None, self.local_tree)

    def apply(self, tree: SyncTree):
        nodes = {n.id: n for n in tree.flatten()}

        for t in [self.notion_tree, self.local_tree]:
            for node in t.traverse():
                ref: SyncNode = nodes.get(node.id)
                if ref is None: continue
                node.metadata_notion = ref.metadata_notion
                node.metadata_local = ref.metadata_local
                node.synced_at = ref.synced_at
