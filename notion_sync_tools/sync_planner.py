import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import partial
from itertools import chain
from operator import is_not
from typing import List, Optional

from notion_sync_tools.sync_tree import SyncNode, SyncNodeType


class SyncActionType(Enum):
    FETCH = 'FETCH'
    DELETE = 'DELETE'
    CONFLICT = 'CONFLICT'


class SyncActionTarget(Enum):
    NOTION = 'NOTION'
    LOCAL = 'LOCAL'


@dataclass
class SyncAction:
    action_type: SyncActionType
    action_target: SyncActionTarget
    node: SyncNode
    changed_at: datetime
    conflicts: List['SyncAction'] = field(default_factory=lambda: [])
    content: Optional[str] = field(default_factory=lambda: '')

    def __str__(self) -> str:
        if self.action_type != SyncActionType.CONFLICT:
            changed_at = self.changed_at.strftime("%Y-%m-%d %H:%M")
            title = self.node.metadata_notion.title if self.action_target == SyncActionTarget.NOTION \
                else self.node.metadata_local.path
            return f'{self.action_type} FROM {self.action_target} FOR {self.node.id}|{title} SINCE {changed_at}'
        else:
            children = ''.join(['\n\t' + str(c) for c in self.conflicts])
            return f'{self.action_type} AT:{children}'

    @property
    def should_create(self) -> bool:
        return self.action_type != SyncActionType.DELETE and (
                (self.action_target == SyncActionTarget.LOCAL and not self.node.metadata_notion) or
                (self.action_target == SyncActionTarget.NOTION and not self.node.metadata_local)
        )

    @staticmethod
    def delete(action_target: SyncActionTarget, node: SyncNode) -> 'SyncAction':
        return SyncAction(SyncActionType.DELETE, action_target, node, datetime.now())

    @staticmethod
    def fetch(action_target: SyncActionTarget, node: SyncNode) -> 'SyncAction':
        return SyncAction(
            SyncActionType.FETCH, action_target, node,
            node.metadata_local.updated_at if action_target == SyncActionTarget.LOCAL
            else node.metadata_notion.updated_at
        )

    @staticmethod
    def conflict(node: SyncNode, actions: List['SyncAction']) -> 'SyncAction':
        return SyncAction(
            SyncActionType.CONFLICT, SyncActionTarget.LOCAL,
            node, max(*map(lambda x: x.changed_at, actions)), actions
        )

    @staticmethod
    def from_node(action_target: SyncActionTarget, node: SyncNode) -> 'SyncAction':
        deleted = node.metadata_local.deleted if action_target == SyncActionTarget.LOCAL \
            else node.metadata_notion.deleted
        if deleted:
            return SyncAction.delete(action_target, node)
        else:
            return SyncAction.fetch(action_target, node)


class SyncPlanner:
    def plan(self, node: SyncNode) -> List[SyncAction]:
        return [
            *self.plan_node(node),
            *chain(*map(self.plan, node.children))
        ]

    def plan_node(self, node: SyncNode) -> List[SyncAction]:
        # Skip nodes nto corresponding to any concrete data
        if not node.node_role:
            return []

        changed_local, changed_notion = node.changed()
        if not changed_local and not changed_notion:
            return []

        local_change = SyncAction.from_node(SyncActionTarget.LOCAL, node) if changed_local else None
        notion_change = SyncAction.from_node(SyncActionTarget.NOTION, node) if changed_notion else None

        if local_change and notion_change and local_change.action_type == notion_change.action_type and \
                local_change.action_type != SyncActionType.DELETE:
            # TODO: a conflict is resolvable if not a NOTE is involved
            return [SyncAction.conflict(node, [local_change, notion_change])]

        return list(filter(partial(is_not, None), [local_change, notion_change]))


class SyncConflictResolver:
    def resolve(self, items: List[SyncAction]) -> List[SyncAction]:
        return list(chain(*map(self.resolve_conflict, items)))

    def resolve_conflict(self, action: SyncAction) -> List[SyncAction]:
        if action.action_type != SyncActionType.CONFLICT:
            return [action]

        if action.node.node_type != SyncNodeType.NOTE:
            logging.info(f'Automatically resolving conflict: \n\t{action}\nReason: Structural Content')
            return action.conflicts

        print(f'Conflict occurred: \n{str(action)}\n')
        while True:
            choice = input('Would you like to prefer [l]ocal changes, [n]otion changes, [s]kip or [a]bort sync:')
            if choice not in 'lnas':
                continue

            if choice == 'l':
                return list(filter(lambda a: a.action_target == SyncActionTarget.NOTION, action.conflicts))
            elif choice == 'n':
                return list(filter(lambda a: a.action_target == SyncActionTarget.LOCAL, action.conflicts))
            elif choice == 's':
                return []
            elif choice == 'a':
                exit(0)
