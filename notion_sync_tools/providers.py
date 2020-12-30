import os
from datetime import datetime
from typing import Optional, Union

from notion_sync_tools.sync_tree import Path, SyncTree, SyncNode, SyncMetadataLocal, TREE_FILENAME


class LocalProvider:
    root_dir: Path

    def __init__(self, root_dir: Path) -> None:
        super().__init__()
        self.root_dir = root_dir

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
        node_path = os.path.join(path, node.metadata_local.path)

        # Check if current node exists
        if not os.path.exists(node_path):
            node.metadata_local.deleted = True
            return node

        if os.path.isfile(node_path):
            node.metadata_local.synced_at = max(
                node.metadata_local.synced_at,
                datetime.fromtimestamp(os.path.getmtime(node_path))
            )
            return node

        # Check for new items
        children = set(child.metadata_local.path for child in node.children)
        for item in os.listdir(os.path.join(path, node.metadata_local.path)):
            if item in children or item == TREE_FILENAME:
                continue

            child = self.create_node(node_path, node, item)
            if child:
                node.children.append(child)

        # Update children
        synced_at = datetime.now().replace(year=1990)
        for child in node.children:
            self.fetch_node(node_path, child)
            synced_at = max(synced_at, child.metadata_local.synced_at)
        node.metadata_local.synced_at = synced_at

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

        return SyncNode(
            parent,
            [],
            'folder' if is_folder else 'file',
            None,
            SyncMetadataLocal(item, datetime.now().replace(year=1990), deleted=False)
        )
