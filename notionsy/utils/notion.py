__all__ = ['get_page_by_name', 'get_prop_by_name', 'iterate', 'filter_date_after', 'find_prop', 'default_dt',
           'to_local_dt']

from copy import copy
from datetime import datetime, timezone
from typing import Union, Optional

from notion.block import Block, CollectionViewPageBlock, CollectionViewBlock, PageBlock
from notion.collection import Collection, CollectionRowBlock, CollectionQuery
from dateutil import tz


def get_page_by_name(name, pages) -> Optional[Block]:
    """
    Retuns a page with a matching title given a list of pages/blocks
    :param name:
    :param pages:
    :return:
    """
    return next(filter(lambda p: p.title == name, pages), None)


def get_prop_by_name(name, schema):
    """
    Returns a propery by a given name
    :param name:
    :param schema:
    :return:
    """
    return next(filter(lambda p: p.name == name, schema), None)


def iterate(page: Union[Block, Collection]):
    """
    Iterates through children of a block or a collection
    :param page:
    :return:
    """
    if isinstance(page, Collection):
        return page.get_rows()
    if isinstance(page, CollectionQuery):
        return iterate(page.collection)
    if isinstance(page, CollectionViewPageBlock) or isinstance(page, CollectionViewBlock):
        return iterate(page.collection)
    if isinstance(page, CollectionRowBlock) or isinstance(page, PageBlock):
        return page.children

    return []


def filter_date_after(property: str, date: datetime):
    """
    Constructs a date is after filter for notion
    :param property:
    :param date:
    :return:
    """
    return {
        "filter": {
            "operator": "date_is_after",
            "value": {
                "type": "exact",
                "value": {
                    "start_date": date.strftime('%Y-%m-%d'),
                    "type": "date"
                }
            }
        },
        "property": property
    }


def find_prop(slug: str, collection: Collection) -> Optional[dict]:
    """
    Returns a collection property given a slug
    :param slug:
    :param collection:
    :return:
    """
    return next(filter(lambda p: p['slug'] == slug, collection.get_schema_properties()), None)


def copy_properties(old: Block, new: Block, depth: int = 1):
    props = list(map(lambda p: p['slug'], old.schema)) if hasattr(old, 'schema') else dir(old)
    for prop in props:
        try:
            if not prop.startswith('_'):
                attr = getattr(old, prop)
                # copying tags creates a whole new set of problems
                if prop != 'tags' and attr != '' and not callable(attr):
                    setattr(new, prop, copy(attr))
            # notion-py raises AttributeError when it can't assign an attribute
        except AttributeError:
            pass

    if depth > 0:
        if bool(old.children):
            for old_child in old.children:
                new_child = new.children.add_new(old_child.__class__)
                copy_properties(old_child, new_child, depth - 1)


def default_dt():
    return datetime.now().replace(year=1990)


def to_local_dt(dt: Optional[datetime]) -> Optional[datetime]:
    return dt.replace(tzinfo=tz.tzutc()).astimezone(tz=tz.tzlocal()).replace(tzinfo=None) if dt else None
