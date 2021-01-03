import io
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from md2notion.NotionPyRenderer import LatexNotionPyRenderer
from md2notion.upload import upload
from notion.block import CollectionViewBlock
from notion.client import NotionClient
from notion.collection import Collection

from notion_sync_tools.sync_mapping import Mapping, NotionResourceMapper
from notion_sync_tools.sync_planner import SyncAction
from notion_sync_tools.sync_tree import SyncNodeType, SyncNode, SyncMetadataNotion, SyncNodeRole

UNIVERSITY_LOCAL_MAPPING = Mapping({r'^.+/$': 'course', r'^.+/.+$': 'lecture'})
UNIVERSITY_NOTION_MAPPING = Mapping({r'^.+ Courses\/.+$': 'course', r'^Lectures\/.+$': 'lecture'})
UNIVERSITY_STRUCTURE_MAPPING = {'course': SyncNodeType.GROUP, 'lecture': SyncNodeType.NOTE}
UNIVERSITY_HIERARCHY = ['course', 'lecture']


@dataclass
class UniversityResourceMapper(NotionResourceMapper):
    client: NotionClient

    def __init__(self, client: NotionClient) -> None:
        super().__init__({})
        self.client = client

    def create_course(self, action: SyncAction):
        parent = self.content_mapping.get(action.node.node_role)
        lecture_block_id = self.content_mapping['lecture'].metadata_notion.id
        lecture_collection = self.client.get_block(lecture_block_id).collection
        course_collection: Collection = self.client.get_block(parent.metadata_notion.id).collection

        page = course_collection.add_row()
        page.title = action.node.metadata_local.path.replace('.md', '')
        cvb: CollectionViewBlock = page.children.add_new(CollectionViewBlock, collection=lecture_collection)
        view = cvb.views.add_new(view_type="list")
        view.set('query2', {'filter': {'filters': [{'filter': {'value': {'type': 'exact',
                                                                         'value': page.id},
                                                               'operator': 'relation_contains'},
                                                    'property': 'TKKM'}],
                                       'operator': 'and'}})

        action.node.metadata_notion = SyncMetadataNotion(
            id=page.id,
            title=page.title,
            updated_at=datetime.now(),
        )

    def update_course(self, action: SyncAction):
        pass

    def create_lecture(self, action: SyncAction):
        lecture_block_id = self.content_mapping['lecture'].metadata_notion.id
        lecture_collection = self.client.get_block(lecture_block_id).collection

        page = lecture_collection.add_row()
        page.title = action.node.metadata_local.path.replace('.md', '')
        page.course = [action.node.parent.metadata_notion.id]
        content = io.StringIO(action.content)
        content.__dict__["name"] = action.node.metadata_local.path.replace('.md', '')
        upload(content, page, notionPyRendererCls=LatexNotionPyRenderer)

        action.node.metadata_notion = SyncMetadataNotion(
            id=page.id,
            title=page.title,
            updated_at=datetime.now(),
            relations={'course': [action.node.parent.metadata_notion.id]}
        )

    def update_lecture(self, action: SyncAction):
        page = self.client.get_block(action.node.metadata_notion.id)
        for c in page.children:
            c.remove()

        content = io.StringIO(action.content)
        content.__dict__["name"] = action.node.metadata_local.path.replace('.md', '')
        upload(content, page, notionPyRendererCls=LatexNotionPyRenderer)
        action.node.metadata_notion.updated_at = datetime.now()
