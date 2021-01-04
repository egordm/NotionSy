import logging
import os
import shutil
import time
from dataclasses import dataclass
from typing import List, Tuple, Dict, Union

from tqdm import tqdm

from notionsy.local_provider import LocalProvider
from notionsy.notion_provider import NotionProvider
from notionsy.sync_planner import SyncAction, SyncActionTarget
from notionsy.sync_tree import SyncNode

Content = str


@dataclass
class Syncer:
    providers: Dict[SyncActionTarget, Union[NotionProvider, LocalProvider]]

    def sync(self, actions: List[SyncAction]):
        targets = set(self.providers.keys())

        for action in tqdm(actions):
            logging.info(f'EXECUTING: {action}')
            self.providers[action.action_target].action_downstream(action)
            other = list((targets - {action.action_target}))[0]
            self.providers[other].action_upstream(action)
            time.sleep(5)
