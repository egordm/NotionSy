import mimetypes
import os
from datetime import datetime
from typing import Optional, Union

from notion_sync_tools.sync_tree import Path, SyncTree, SyncNode, SyncMetadataLocal, TREE_FILENAME, Mapping, \
    SyncNodeType


class LocalProvider:
    root_dir: Path
    mapping: Mapping

    def __init__(self, root_dir: Path, mapping: Mapping) -> None:
        super().__init__()
        self.root_dir = root_dir
        self.mapping = mapping

    def fetch_tree(self, tree: SyncTree) -> SyncTree:
        """
        Syncs all the local data to the given sync tree
        :param tree:
        :return:
        """
        return self.fetch_node(self.root_dir, tree)

    def fetch_node(self, path: Path, node: Union[SyncNode, SyncTree]) -> Union[SyncNode, SyncTree]:
        """
        Syncs local data to the given tree
        :param path:
        :param node:
        :return:
        """
        if node.metadata_local.deleted:
            return node

        node_path = os.path.join(path, node.metadata_local.path)

        # Check if current node exists
        if not os.path.exists(node_path):
            node.metadata_local.deleted = True
            return node

        # Update node
        node.node_role = self.mapping.match(format_path(self.root_dir, os.path.relpath(node_path, self.root_dir)))

        # Handle standalone files (leaves)
        if os.path.isfile(node_path):
            node.metadata_local.updated_at = max(
                node.metadata_local.updated_at,
                datetime.fromtimestamp(os.path.getmtime(node_path))
            )
            return node

        # Check for new items
        children = {child.metadata_local.path: child for child in node.children}
        for item in os.listdir(os.path.join(path, node.metadata_local.path)):
            # Skip internal files
            if item == TREE_FILENAME:
                continue

            # Remove valid children from the memo
            if item in children:
                children.pop(item)
                continue

            # Create the new child since it doent exist yet
            child = self.create_node(node_path, node, item)
            if child:
                node.children.append(child)

        # Unused children are deleted
        for (_, child) in children.items():
            child.metadata_notion.deleted = True

        # Update children
        for child in node.children:
            self.fetch_node(node_path, child)
        node.collect_updated_at(local=True)

        return node

    def create_node(self, path: Path, parent: SyncNode, item: Path) -> Optional[SyncNode]:
        """
        Creates a new local node
        :param path:
        :param parent:
        :param item:
        :return:
        """
        node_path = os.path.join(path, item)
        is_folder = os.path.isdir(node_path)
        mime, _ = mimetypes.guess_type(node_path)

        # Only folders and textual files allowed
        if not is_folder and not mime.startswith('text'):
            return None

        return SyncNode(
            parent=parent, node_type=SyncNodeType.GROUP if is_folder else SyncNodeType.NOTE,
            metadata_local=SyncMetadataLocal(item)
        )


def format_path(root_dir: Path, path: Path) -> Path:
    if path == '.':
        return '.'
    if os.path.isdir(os.path.join(root_dir, path)):
        return path.rstrip('/') + '/'
    return path
