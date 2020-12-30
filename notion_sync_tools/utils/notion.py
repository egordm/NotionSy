__all__ = ['get_page_by_name', 'get_prop_by_name', 'iterate', 'filter_date_after', 'find_prop']

from datetime import datetime
from typing import Union, Optional

from notion.block import Block, CollectionViewPageBlock, CollectionViewBlock, PageBlock
from notion.collection import Collection, CollectionRowBlock


def get_page_by_name(name, pages):
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
                    "start_date": date.strftime('%y-%m-%d'),
                    "type": "datetime"
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
