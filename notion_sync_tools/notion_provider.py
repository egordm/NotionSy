from datetime import datetime
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
        page = self.client.get_block(tree.metadata_notion.id)
        children = {child.metadata_notion.id: child for child in tree.children}

        # Create new children or reuse existing ones if needed
        for group in iterate(page):
            if group.id in children:
                node = children.pop(group.id)
            else:
                node = self.create_node(group.id, tree)
                tree.children.append(node)

            self.fetch_group(node, group)

        # Unused children are deleted
        for (_, child) in children:
            child.metadata_notion.deleted = True

        return tree

    def fetch_group(self, node: SyncNode, group: CollectionRowBlock) -> Union[SyncNode, SyncTree]:
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
                child = self.create_node(group.id, node)
                node.children.append(child)
            self.fetch_item(node_path, child, item)
            synced_at = max(synced_at, child.metadata_notion.synced_at)
        node.metadata_notion.synced_at = synced_at

        # Unused children are deleted
        for (_, child) in children:
            child.metadata_notion.deleted = True

        return node

    def fetch_item(self, group_path: str, node: SyncNode, item: CollectionRowBlock):
        node_path = f'{group_path}/{item.title}'
        node.node_role = self.mapping.match(node_path)
        node.metadata_notion = SyncMetadataNotion(
            item.id, max(node.metadata_notion.synced_at, item.updated or node.metadata_notion.synced_at)
        )
        node.metadata_notion.relations = {
            role: getattr(item, role)
            for role in self.mapping.roles() if hasattr(item, role)
        }
        return node

    def create_node(self, id: GUID, parent: SyncNode):
        return SyncNode(
            parent=parent, node_type='group',
            metadata_notion=SyncMetadataNotion(id)
        )
