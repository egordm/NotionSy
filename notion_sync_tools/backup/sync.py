import enum
import itertools
from dataclasses import dataclass
from functools import cached_property
from typing import Union

from notion.block import Block, CollectionViewPageBlock, CollectionViewBlock, PageBlock
from notion.client import NotionClient
from notion.collection import CollectionRowBlock, Collection


class RecurseMode(enum.Enum):
    NoRecurse = 0
    Self = 1
    Children = 2
    SelfAndChildren = 3


@dataclass
class NotionProvider:
    client: NotionClient
    root_url: str

    @cached_property
    def root(self):
        return self.client.get_block(self.root_url)

    def iterate(self, item: Union[Block, Collection]):
        if isinstance(item, Collection):
            return item.get_rows()
        if isinstance(item, CollectionViewPageBlock) or isinstance(item, CollectionViewBlock):
            return self.iterate(item.collection)
        if isinstance(item, CollectionRowBlock) or isinstance(item, PageBlock):
            return item.children
        return []

    def iterate_recursively(self, item, check_node_fn, parents=None, first=True):
        if not parents:
            parents = []

        if not first:
            mode = check_node_fn(item, parents)
            if mode == RecurseMode.NoRecurse:
                return

            if mode.value & RecurseMode.Self.value:
                yield item, parents

        if first or mode.value & RecurseMode.Children.value:
            yield from itertools.chain.from_iterable([
                self.iterate_recursively(child, check_node_fn, [*parents, item], False) for child in self.iterate(item)
                if not next(filter(lambda p: p.id == child.id, parents), None)
            ])


def sync_iterate():
    pass
