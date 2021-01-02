import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Union

from notion.client import NotionClient

from notion_sync_tools.local_provider import LocalProvider
from notion_sync_tools.notion2md import NotionMarkdownExporter
from notion_sync_tools.notion_provider import NotionProvider
from notion_sync_tools.sync_planner import SyncAction, SyncActionTarget
from notion_sync_tools.sync_tree import SyncNode, SyncNodeType, Path, SyncMetadataLocal, SyncMetadataNotion

Content = str


@dataclass
class Syncer:
    providers: Dict[SyncActionTarget, Union[NotionProvider, LocalProvider]]

    def sync(self, actions: List[SyncAction]) -> List[Tuple[SyncAction, SyncNode]]:
        targets = set(self.providers.keys())

        for action in actions:
            self.providers[action.action_target].action_downstream(action)
            other = list((targets - {action.action_target}))[0]
            self.providers[other].action_upstream(action)
