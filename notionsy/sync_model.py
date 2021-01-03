from dataclasses import dataclass

from notionsy.local_provider import LocalProvider
from notionsy.notion_provider import NotionProvider
from notionsy.sync_mapping import SyncConfig
from notionsy.sync_merger import SyncMerger
from notionsy.sync_planner import SyncPlanner, SyncConflictResolver
from notionsy.syncer import Syncer


class SyncModel:
    sync_config: SyncConfig
    local_provider: LocalProvider
    notion_provider: NotionProvider
    merger: SyncMerger
    planner: SyncPlanner
    resolver: SyncConflictResolver
    syncer: Syncer
