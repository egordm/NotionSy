from abc import ABC, abstractmethod
from dataclasses import dataclass

from notionsy.sync_planner import SyncAction
from notionsy.sync_tree import SyncTree


@dataclass
class BaseProvider(ABC):
    @abstractmethod
    def fetch_tree(self, tree: SyncTree) -> SyncTree:
        pass

    @abstractmethod
    def action_upstream(self, action: SyncAction):
        pass

    @abstractmethod
    def action_downstream(self, action: SyncAction):
        pass
