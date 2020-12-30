import logging
from copy import copy
from dataclasses import dataclass
from datetime import datetime
from typing import List, Union, Dict, Optional, Any

import yaml
from notion.block import Block
from notion.collection import Collection

GUID = str
Path = str
NotionElement = Union[Block, Collection]





@dataclass
class SyncNode(SecretYamlObject):
    hidden_fields = ["parent", "notion_item"]
    yaml_tag = u'!SyncNode'
    guid: GUID
    notion_item: NotionElement
    title: str
    updated_at: Optional[datetime]
    local_path: Path
    parent: 'SyncNode'
    children: List['SyncNode']
    metadata: Dict[str, Any]

    def find_child(self, node: 'SyncNode') -> Optional[int]:
        for i, child in enumerate(self.children):
            if child.guid == node.guid:
                return i
        return None

    @staticmethod
    def from_notion(item: NotionElement, parent=None, local_path=None) -> 'SyncNode':
        return SyncNode(
            item.id,
            item,
            item.title,
            item.updated if hasattr(item, 'updated') else None,
            local_path,
            parent,
            []
        )


class SyncTree:
    lookup: Dict[GUID, SyncNode]
    root: SyncNode

    def __init__(self, root: SyncNode) -> None:
        super().__init__()
        self.root = root
        self.lookup = {root.guid: root}

    def upsert(self, node: SyncNode, parent_id: GUID):
        if parent := self.lookup.get(parent_id, None):
            node.parent = parent
            self.lookup[node.guid] = node
            if index := parent.find_child(node):
                logging.debug(f'Updates existing child: {node.guid} with parent {parent_id}')
                parent.children[index] = node
            else:
                logging.debug(f'Added new child: {node.guid} with parent {parent_id}')
                parent.children.append(node)
        else:
            logging.warning(f'Found a loose node: {node.guid} with parent {parent_id}')

    def write(self, file_path):
        with open(file_path, 'w') as f:
            yaml.dump(self.root, f, default_flow_style=False)
