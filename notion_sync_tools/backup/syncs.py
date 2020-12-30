import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Iterable, List

from notion.collection import ListView, Collection

from notion_sync_tools.structures import Path, SyncNode, SyncTree, NotionElement
from notion_sync_tools.sync import NotionProvider, RecurseMode


def filter_date_after(property: str, date: datetime):
    return {
        "filter": {
            "operator": "date_is_after",
            "value": {
                "type": "exact",
                "value": {
                    "start_date": date.strftime('%y-%m-%d'),
                    "type": "datetime"
                }
            }
        },
        "property": property
    }


def find_prop(slug: str, collection: Collection) -> Optional[dict]:
    return next(filter(lambda p: p['slug'] == slug, collection.get_schema_properties()), None)


def query_resource(view: ListView, from_date: Optional[datetime] = None) -> Iterable[NotionElement]:
    params = {
        "sort": [],
        "filter": {"filters": [], "operator": "and"}
    }
    if updated_prop := find_prop('updated', view.collection):
        params['sort'].append({"direction": "descending", "property": updated_prop['id']})
        if from_date:
            params['filter']['filters'].append(filter_date_after(updated_prop['id'], from_date))

    yield from view.build_query(**params).execute()


@dataclass
class UniversitySync:
    provider: NotionProvider
    local_path: Path

    def is_courses_collection(self, item, parents):
        return item.title.endswith('Courses') and len(parents) == 1

    def iter_courses(self, **kwargs):
        for container in filter(lambda c: c.title.endswith('Courses'), self.provider.root.children):
            if view := next(filter(lambda v: isinstance(v, ListView), container.views)):
                yield from query_resource(view, **kwargs)

    def iter_lectures(self, **kwargs):
        if container := next(filter(lambda c: c.title == 'Lectures', self.provider.root.children), None):
            if view := next(filter(lambda v: isinstance(v, ListView), container.views)):
                yield from query_resource(view, **kwargs)

    def downstream_iter(self):
        def iter_filter(item, parents):
            if len(parents) == 1 or self.is_courses_collection(item, parents):
                if self.is_courses_collection(item, parents):
                    return RecurseMode.SelfAndChildren
                return RecurseMode.NoRecurse

            return RecurseMode.SelfAndChildren

        return self.provider.iterate_recursively(
            self.provider.root,
            iter_filter
        )

    def downsync(self):
        tree: SyncTree = SyncTree(SyncNode.from_notion(self.provider.root))

        for item, [*parents, parent] in self.downstream_iter():
            print(item)
            tree.upsert(SyncNode.from_notion(item), parent.id)

        tree.write(os.path.join(self.local_path, '.sync.yml'))
        return tree
