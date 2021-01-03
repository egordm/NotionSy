import logging
import mimetypes
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union

from notion_sync_tools.base_provider import BaseProvider
from notion_sync_tools.sync_planner import SyncAction, SyncActionTarget, SyncActionType
from notion_sync_tools.sync_tree import Path, SyncTree, SyncNode, SyncMetadataLocal, TREE_FILENAME, SyncNodeType, \
    INTERNAL_FILES
from notion_sync_tools.sync_mapping import Mapping, SyncModel


@dataclass
class LocalProvider(BaseProvider):
    model: SyncModel

    @property
    def mapping(self) -> Mapping:
        return self.model.local_mapping

    @property
    def root_dir(self) -> Path:
        return self.model.root_dir

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
            if item in INTERNAL_FILES:
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

    def action_upstream(self, action: SyncAction):
        assert action.action_target == SyncActionTarget.NOTION
        if action.action_type == SyncActionType.FETCH:
            if action.node.node_type == SyncNodeType.NOTE:
                filename = f'{action.node.metadata_notion.title}.md'
                filepath = os.path.join(self.root_dir, action.node.local_dir(), filename)
                with open(filepath, 'w') as f:
                    f.write(action.content)
                action.node.metadata_local = SyncMetadataLocal(
                    path=filename,
                    updated_at=datetime.now()
                )
            elif action.node.node_type == SyncNodeType.GROUP:
                filename = action.node.metadata_notion.title
                filepath = os.path.join(self.root_dir, action.node.local_dir(), filename)
                os.makedirs(filepath, exist_ok=True)
                action.node.metadata_local = SyncMetadataLocal(
                    path=filename,
                    updated_at=datetime.now()
                )

    def action_downstream(self, action: SyncAction):
        assert action.action_target == SyncActionTarget.LOCAL
        if action.action_type == SyncActionType.DELETE:
            # Delete a node
            logging.debug(f'ACTION - NOTION: Deleting local node: {action.node.metadata_notion.id}')
            shutil.rmtree(os.path.join(self.root_dir, action.node.local_path()))
        elif action.action_type == SyncActionType.FETCH:
            if action.node.node_type == SyncNodeType.NOTE:
                with open(os.path.join(self.root_dir, action.node.local_path()), 'r') as f:
                    action.content = f.read()


def format_path(root_dir: Path, path: Path) -> Path:
    if path == '.':
        return '.'
    if os.path.isdir(os.path.join(root_dir, path)):
        return path.rstrip('/') + '/'
    return path
