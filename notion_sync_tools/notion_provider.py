import io
import logging
import os
from dataclasses import field, dataclass
from datetime import datetime
from itertools import groupby
from typing import Union, Dict, List

from md2notion.NotionPyRenderer import LatexNotionPyRenderer
from md2notion.upload import upload
from notion.block import CollectionViewBlock
from notion.client import NotionClient
from notion.collection import CollectionRowBlock, Collection

from notion_sync_tools.base_provider import BaseProvider
from notion_sync_tools.notion2md import NotionMarkdownExporter
from notion_sync_tools.sync_planner import SyncAction, SyncActionTarget, SyncActionType
from notion_sync_tools.sync_tree import SyncTree, GUID, SyncNode, SyncMetadataNotion, SyncNodeType, \
    SyncNodeRole, Path
from notion_sync_tools.sync_mapping import Mapping, NotionResourceMapper, ResourceAction, SyncModel
from notion_sync_tools.utils.notion import iterate


@dataclass
class NotionProvider(BaseProvider):
    client: NotionClient
    model: SyncModel

    @property
    def mapping(self) -> Mapping:
        return self.model.notion_mapping

    @property
    def root_dir(self) -> Path:
        return self.model.root_dir

    def fetch_tree(self, tree: SyncTree) -> SyncTree:
        """
        Syncs the whole tree based on the given root page
        :param tree:
        :return:
        """
        page = self.client.get_block(tree.metadata_notion.id)
        children = {child.metadata_notion.id: child for child in tree.children}
        tree.metadata_notion.title = page.title

        # Create new children or reuse existing ones if needed
        for group in iterate(page):
            if group.id in children:
                node = children.pop(group.id)
            else:
                node = self.create_node(group.id, group.title, tree)
                tree.children.append(node)

            self.fetch_group(node, group)

        # Unused children are deleted
        for (_, child) in children.items():
            child.metadata_notion.deleted = True

        self.extract_role_parents(tree)
        self.link_relations(tree)
        tree.collect_updated_at(notion=True, recursive=True)
        return tree

    def fetch_group(self, node: SyncNode, group: CollectionRowBlock) -> Union[SyncNode, SyncTree]:
        """
        Syncs inline listviews within the main page
        :param node:
        :param group:
        :return:
        """
        if node.metadata_notion.deleted:
            return node

        node_path = group.title
        node.node_role = self.mapping.match(node_path)

        children = {child.metadata_notion.id: child for child in node.children}
        notion_children = group.views[0].build_query(
            sort=[{"direction": "descending", "property": "updated"}],
            # filter={"filters": [
            #     filter_date_after('updated', node.metadata_notion.updated_at)
            # ], "operator": "and"}
        )

        # Create new children or reuse existing ones if needed
        for item in iterate(notion_children):
            if group.id in children:
                child = children.pop(group.id)
            else:
                child = self.create_node(item.id, item.title, node)
                node.children.append(child)
            self.fetch_item(node_path, child, item)

        # Unused children are deleted
        for (_, child) in children:
            child.metadata_notion.deleted = True

        node.collect_updated_at(notion=True)

        return node

    def fetch_item(self, group_path: str, node: SyncNode, item: CollectionRowBlock):
        """
        Syncs individual pages
        :param group_path:
        :param node:
        :param item:
        :return:
        """
        if node.metadata_notion.deleted:
            return node

        node_path = f'{group_path}/{item.title}'
        node.node_role = self.mapping.match(node_path)
        node.node_type = self.model.structure_types[node.node_role]
        node.metadata_notion = SyncMetadataNotion(
            item.id, item.title, max(node.metadata_notion.updated_at, item.updated or node.metadata_notion.updated_at)
        )
        node.metadata_notion.relations = {
            role: [related.id for related in getattr(item, role)]
            for role in self.mapping.roles() if hasattr(item, role)
        }
        return node

    def link_relations(self, tree: SyncTree):
        """
        Adds addittional parent to child links for linked items
        :param tree:
        :return:
        """
        grouped = {k: list(v) for k, v in groupby(tree.flatten(), lambda i: i.node_role)}
        grouped.pop(None)

        for items in grouped.values():
            for item in items:
                if len(item.metadata_notion.relations) == 0:
                    continue

                for parent_role, parents in item.metadata_notion.relations.items():
                    parent_items = filter(lambda i: i.metadata_notion.id in parents, grouped[parent_role])
                    for parent in parent_items:
                        # TODO: do we need to check for duplicates?
                        item.parent = parent
                        parent.children.append(item)

    def create_node(self, id: GUID, title: str, parent: SyncNode):
        return SyncNode(
            parent=parent, node_type=SyncNodeType.GROUP,
            metadata_notion=SyncMetadataNotion(id, title=title)
        )

    def extract_role_parents(self, tree: SyncTree):
        grouped = {k: list(v) for k, v in groupby(tree.flatten(), lambda i: i.node_role)}
        grouped.pop(None)

        def find_parent(nodes: List[SyncNode]) -> SyncNode:
            for node in nodes:
                if node.parent and not node.parent.node_role:
                    return node.parent

        self.model.resource_mapper.content_mapping = {k: find_parent(v) for k, v in grouped.items()}

    def action_upstream(self, action: SyncAction):
        assert action.action_target == SyncActionTarget.LOCAL
        if action.action_type == SyncActionType.FETCH and action.node.node_role:
            resource_action = ResourceAction.CREATE if action.should_create else ResourceAction.UPDATE
            self.model.resource_mapper.execute(resource_action, action.node.node_role, action)
            action.node.synced_at = action.changed_at

    def action_downstream(self, action: SyncAction):
        assert action.action_target == SyncActionTarget.NOTION
        if action.action_type == SyncActionType.DELETE:
            # Delete a node
            logging.debug(f'ACTION - NOTION: Deleting notion node: {action.node.metadata_notion.id}')
            self.client.get_block(action.node.metadata_notion.id).remove()
        elif action.action_type == SyncActionType.FETCH:
            if action.node.node_type == SyncNodeType.NOTE:
                exporter = NotionMarkdownExporter(
                    image_dir=os.path.join(self.root_dir, action.node.local_dir(), 'resources')
                )
                page = self.client.get_block(action.node.metadata_notion.id)
                action.content = exporter.export_page(page)
