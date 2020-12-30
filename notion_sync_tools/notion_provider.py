from typing import Union, List

from notion.client import NotionClient

from notion_sync_tools.sync_tree import SyncTree, GUID, SyncNode, Path


class NotionProvider:
    client: NotionClient

    def fetch_tree(self, tree: SyncTree, mapping) -> SyncTree:
        return self.fetch_node('', tree)

    def fetch_node(self, path: Path, node: Union[SyncNode, SyncTree]) -> Union[SyncNode, SyncTree]:
        # Check whether node is present in notion
        if not node.notion_synced_at:
            return node



