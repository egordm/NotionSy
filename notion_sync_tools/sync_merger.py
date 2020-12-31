import logging
from typing import Optional, Union, List

from notion_sync_tools.sync_tree import SyncTree, SyncMetadataNotion, SyncMetadataLocal, SyncMetadata, SyncNodeRole, \
    SyncNode


class SyncMerger:
    def merge_nodes(self, hierarchy: List[SyncNodeRole], parent: SyncNode, tl: SyncNode, tr: SyncNode) -> SyncNode:
        res = SyncNode(
            parent=parent,
            node_type=tl.node_type,
            node_role=tl.node_role,
            metadata_notion=self.merge_metadata(tl.metadata_notion, tr.metadata_notion),
            metadata_local=self.merge_metadata(tl.metadata_local, tl.metadata_local)
        )

        # If the hierarchy has ended we do not recurse into childrem
        if len(hierarchy) == 0:
            return res

        # Try merging children (left is the preferred choice in conflict)
        root_role, *hierarchy = hierarchy
        logging.debug(f'Merging children for node_role: {root_role}')
        lchildren = {k: v for (k, v) in enumerate(tl.flatten(lambda item: item.node_role == root_role))}
        rchildren = {k: v for (k, v) in enumerate(tr.flatten(lambda item: item.node_role == root_role))}
        for k, lc in lchildren.items():
            rck = next(filter(lambda k: self.match_nodes(lc, rchildren[k]), rchildren.keys()), None)
            if rck:
                rc = rchildren.pop(rck)
                lc = self.merge_nodes(hierarchy, res, lc, rc)  # TODO implement
            lc.parent = res
            res.children.append(lc)

        # Add remaining children from the rhs
        for rc in rchildren.values():
            rc.parent = res
            res.children.append(rc)

        return res

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
