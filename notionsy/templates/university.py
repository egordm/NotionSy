import io
import logging
import time
from dataclasses import dataclass
from datetime import datetime

from md2notion.NotionPyRenderer import LatexNotionPyRenderer
from md2notion.upload import upload
from notion.block import CollectionViewBlock, Block
from notion.client import NotionClient
from notion.collection import Collection

from notionsy.sync_mapping import Mapping, NotionResourceMapper, SyncConfig
from notionsy.sync_planner import SyncAction
from notionsy.sync_tree import SyncNodeType, SyncMetadataNotion, Path, GUID

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
        self.upload_content(
            page.id,
            action.content,
            action.node.metadata_local.path.replace('.md', ''),
            False
        )

        action.node.metadata_notion = SyncMetadataNotion(
            id=page.id,
            title=page.title,
            updated_at=datetime.now(),
            relations={'course': [action.node.parent.metadata_notion.id]}
        )

    def update_lecture(self, action: SyncAction):
        self.upload_content(
            action.node.metadata_notion.id,
            action.content,
            action.node.metadata_local.path.replace('.md', ''),
            True
        )
        action.node.metadata_notion.updated_at = datetime.now()

    def upload_content(self, page_id: GUID, content: str, name: str, clear: bool = True) -> Block:
        while True:
            try:
                page = self.client.get_block(page_id, force_refresh=True)
                if clear:
                    for child in page.children:
                        child.remove()
                time.sleep(2)
                contentFile = io.StringIO(content)
                contentFile.__dict__["name"] = name
                upload(contentFile, page, notionPyRendererCls=LatexNotionPyRenderer)
                break
            except Exception as e:
                logging.error(f'Error occurred while uploading content: {e}')
                clear = True
                time.sleep(10)
        return page


def build_config(root_dir: Path, notion_root: GUID, client: NotionClient) -> SyncConfig:
    return SyncConfig(
        root_dir,
        notion_root,
        UNIVERSITY_LOCAL_MAPPING,
        UNIVERSITY_NOTION_MAPPING,
        UNIVERSITY_STRUCTURE_MAPPING,
        UNIVERSITY_HIERARCHY,
        UniversityResourceMapper(client=client)
    )
