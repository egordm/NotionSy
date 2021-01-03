import logging
from typing import Optional, List, Dict

from notion_sync_tools.sync_tree import SyncMetadataNotion, SyncMetadataLocal, SyncMetadata, SyncNodeRole, \
    SyncNode
from notion_sync_tools.utils.notion import default_dt


class SyncMerger:
    def merge_nodes(
            self, hierarchy: List[SyncNodeRole], tl: SyncNode, tr: SyncNode, parent: Optional[SyncNode] = None
    ) -> SyncNode:
        """
        Merges two trees given a role hierarchy
        :param hierarchy:
        :param parent:
        :param tl:
        :param tr:
        :return:
        """
        res = SyncNode(
            id=tl.id,
            parent=parent,
            node_type=tl.node_type,
            node_role=tl.node_role,
            metadata_notion=self.merge_metadata(tl.metadata_notion, tr.metadata_notion),
            metadata_local=self.merge_metadata(tl.metadata_local, tl.metadata_local),
            synced_at=max(tl.synced_at or default_dt(), tr.synced_at or default_dt())
        )
        tl.copy_metadata_from(res)
        tr.copy_metadata_from(res)

        # If the hierarchy has ended we do not recurse into childrem
        if len(hierarchy) == 0:
            return res

        # Try merging children (left is the preferred choice in conflict)
        root_role, *hierarchy = hierarchy
        logging.debug(f'Merging children for node_role: {root_role}')
        # TODO: restrict to nodes which are not separated by a roleassigned node within the path
        match_role = lambda item: item.node_role == root_role
        lchildren: Dict[str, SyncNode] = {k: v for (k, v) in enumerate(tl.flatten(match_role))}
        rchildren: Dict[str, SyncNode] = {k: v for (k, v) in enumerate(tr.flatten(match_role))}
        for k, lc in lchildren.items():
            rck = next(filter(lambda k: self.match_nodes(lc, rchildren[k]), rchildren.keys()), None)
            if rck is not None:
                rc = rchildren.pop(rck)
                lc = self.merge_nodes(hierarchy, lc, rc, res)  # TODO implement
            else:
                lc = self.merge_branch(hierarchy, lc, res)
            lc.parent = res
            res.children.append(lc)

        # Add remaining children from the rhs
        for rc in rchildren.values():
            res.children.append(self.merge_branch(hierarchy, rc, res))

        return res

    def merge_branch(
            self, hierarchy: List[SyncNodeRole], tl: SyncNode, parent: Optional[SyncNode] = None
    ) -> SyncNode:
        res = tl.clone_childless(parent)

        # If the hierarchy has ended we do not recurse into childrem
        if len(hierarchy) == 0:
            return res

        # Try merging children (left is the preferred choice in conflict)
        root_role, *hierarchy = hierarchy
        match_role = lambda item: item.node_role == root_role
        # Add remaining children
        for c in tl.flatten(match_role):
            res.children.append(self.merge_branch(hierarchy, c, res))

        return res

    def match_nodes(self, nl: SyncNode, nr: SyncNode):
        """
        Checks whether the two nodes correspond to the same entity by checking unique items first
        and then by matching their titles / filenames
        :param nl:
        :param nr:
        :return:
        """
        if nl.id == nr.id:
            return True
        if nl.metadata_local and nr.metadata_local and nl.metadata_local.path == nr.metadata_local.path:
            return True
        if nl.metadata_notion and nr.metadata_notion and nl.metadata_notion.id == nr.metadata_notion.id:
            return True

        def fuzzy_match(ml: SyncMetadataLocal, mr: SyncMetadataNotion):
            return ml.path.replace('.md', '') == mr.title

        if nl.metadata_local and not nr.metadata_local and nr.metadata_notion and not nl.metadata_notion:
            return fuzzy_match(nl.metadata_local, nr.metadata_notion)
        if nr.metadata_local and not nl.metadata_local and nl.metadata_notion and not nr.metadata_notion:
            return fuzzy_match(nr.metadata_local, nl.metadata_notion)
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

        return mr if mr.updated_at > ml.updated_at else ml
