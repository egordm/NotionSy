from datetime import datetime
from itertools import groupby
from typing import Union, List

from notion.client import NotionClient
from notion.collection import CollectionRowBlock

from notion_sync_tools.sync_tree import SyncTree, GUID, SyncNode, Path, Mapping, SyncMetadataNotion
from notion_sync_tools.utils.notion import iterate, filter_date_after, find_prop


class NotionProvider:
    client: NotionClient
    mapping: Mapping

    def __init__(self, client: NotionClient, mapping: Mapping) -> None:
        super().__init__()
        self.client = client
        self.mapping = mapping

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

        self.link_relations(tree)

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
            #     filter_date_after('updated', node.metadata_notion.synced_at)
            # ], "operator": "and"}
        )

        # Create new children or reuse existing ones if needed
        synced_at = datetime.now().replace(year=1990)
        for item in iterate(notion_children):
            if group.id in children:
                child = children.pop(group.id)
            else:
                child = self.create_node(item.id, item.title, node)
                node.children.append(child)
            self.fetch_item(node_path, child, item)
            synced_at = max(synced_at, child.metadata_notion.synced_at)
        node.metadata_notion.synced_at = synced_at

        # Unused children are deleted
        for (_, child) in children:
            child.metadata_notion.deleted = True

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
        node.metadata_notion = SyncMetadataNotion(
            item.id, item.title, max(node.metadata_notion.synced_at, item.updated or node.metadata_notion.synced_at)
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
        grouped = {k: list(v) for k, v in groupby(tree.flatten(), lambda item: item.node_role)}
        grouped.pop(None)

        for items in grouped.values():
            for item in items:
                if len(item.metadata_notion.relations) == 0:
                    continue

                for parent_role, parents in item.metadata_notion.relations.items():
                    parent_items = filter(lambda i: i.metadata_notion.id in parents, grouped[parent_role])
                    for parent in parent_items:
                        # TODO: do we need to check for duplicates?
                        parent.children.append(item)
                        items.parent = parent

    def create_node(self, id: GUID, title: str, parent: SyncNode):
        return SyncNode(
            parent=parent, node_type='group',
            metadata_notion=SyncMetadataNotion(id, title=title)
        )
