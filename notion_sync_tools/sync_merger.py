from typing import Optional, Union, List

from notion_sync_tools.sync_tree import SyncTree, SyncMetadataNotion, SyncMetadataLocal, SyncMetadata, SyncNodeRole, \
    SyncNode


class SyncMerger:
    def merge(self, hierarchy: List[SyncNodeRole], tl: SyncTree, tr: SyncTree):
        root_role, *hierarchy = hierarchy
        res = SyncTree(
            node_type='root',
            metadata_notion=self.merge_metadata(tl.metadata_notion, tr.metadata_notion),
            metadata_local=self.merge_metadata(tl.metadata_local, tl.metadata_local)
        )
        lchildren = {k: v for (k, v) in enumerate(tl.flatten(lambda item: item.node_role == root_role))}
        rchildren = {k: v for (k, v) in enumerate(tr.flatten(lambda item: item.node_role == root_role))}
        children = []
        for k, lc in lchildren.items():
            rck = next(filter(lambda rck: self.match_nodes(lc, rchildren[rck]), rchildren.keys()), None)
            if rck:
                rc = rchildren.pop(rck)
                lc = self.merge(lc, rc)  # TODO implement
            children.append(lc)
        children.append(rchildren.values())

    def match_nodes(self, nl: SyncNode, nr: SyncNode):
        if nl.metadata_local and nr.metadata_local and nl.metadata_local.path == nr.metadata_local.path:
            return True
        if nl.metadata_notion and nr.metadata_notion and nl.metadata_notion.id == nr.metadata_notion.id:
            return True

        def fuzzy_match(ml: SyncMetadataLocal, mr: SyncMetadataNotion):
            return ml.path.replace('.md', '') == mr.title

        if nl.metadata_local and not nr.metadata_local and nl.metadata_notion and not nr.metadata_notion:
            return fuzzy_match(nl.metadata_local, nr.metadata_notion)
        if not nl.metadata_local and nr.metadata_local and not nl.metadata_notion and nr.metadata_notion:
            return fuzzy_match(nl.metadata_local, nr.metadata_notion)
        return False

    def merge_metadata(self, ml: Optional[SyncMetadata], mr: Optional[SyncMetadata]):
        """
        Returns the fresher version of metadata. Prefers left if there is a tie
        :param ml:
        :param mr:
        :return:
        """
        # Handle basic cases
        if ml is None and mr is None:
            return None

        if ml is None or mr is None:
            return mr if ml is None else mr

        return mr if mr.synced_at < ml.synced_at else ml
