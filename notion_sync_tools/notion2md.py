import mimetypes
import os
import uuid
from dataclasses import field, dataclass
from typing import List

import requests
from notion.block import Block, HeaderBlock, SubheaderBlock, SubsubheaderBlock, TextBlock, BookmarkBlock, VideoBlock, \
    BulletedListBlock, NumberedListBlock, ImageBlock, CodeBlock, EquationBlock, DividerBlock, TodoBlock, QuoteBlock, \
    ColumnBlock, ColumnListBlock, FileBlock, AudioBlock, PDFBlock, GistBlock


@dataclass
class NotionMarkdownExporter:
    image_dir: str
    num_index_stack: List[int] = field(default_factory=lambda: [1])

    def export_block(self, block: Block, indent: int = 0) -> str:
        """
        Renders a block to markdown
        :param block:
        :param indent:
        :return:
        """
        res = '\t' * indent
        title = self.preprocess_markdown(block.title) if hasattr(block, 'title') else ''

        if isinstance(block, HeaderBlock):
            res += f'\n# {title}'
        elif isinstance(block, SubheaderBlock):
            res += f'\n## {title}'
        elif isinstance(block, SubsubheaderBlock):
            res += f'\n### {title}'
        elif isinstance(block, TextBlock):
            res += title
        elif isinstance(block, BookmarkBlock):
            res += link_format(title, block.link)
        elif isinstance(block, VideoBlock) or isinstance(block, FileBlock) or isinstance(block, AudioBlock) or \
                isinstance(block, PDFBlock) or isinstance(block, GistBlock):
            res += link_format(block.source, block.source)
        elif isinstance(block, BulletedListBlock):
            res += f'* {title}'
            res += self.export_blocks(block.children, indent + 1)
        elif isinstance(block, NumberedListBlock):
            res += f'{self.num_index_stack[-1]}. {title}'
            self.num_index_stack[-1] += 1
            res += self.export_blocks(block.children, indent + 1)
        elif isinstance(block, ImageBlock):
            img_path = self.image_export(block.caption, block.source)
            res += f'\n!{link_format(block.caption or img_path, img_path)}'
        elif isinstance(block, CodeBlock):
            res += f'\n```{block.language}\n{block.title}\n```'
        elif isinstance(block, EquationBlock):
            res += f'\n$$\n{block.latex}\n$$'
        elif isinstance(block, DividerBlock):
            res += '---'
        elif isinstance(block, TodoBlock):
            res += f'- [x] {title}' if block.checked else f'- [ ] {title}'
        elif isinstance(block, QuoteBlock):
            res += f'\n> {title}'

        return res

    def export_blocks(self, blocks: List[Block], indent: int = 0):
        """
        Renders a list of blocks to markdown
        :param blocks:
        :param indent:
        :return:
        """
        if len(blocks) == 0:
            return ''
        res = '' if indent == 0 else '\n'
        self.num_index_stack.append(1)
        for block in blocks:
            if block != blocks[0]:
                res += '\n'
            res += self.export_block(block, indent)
        self.num_index_stack.pop()
        return res

    def export_page(self, page: Block):
        """
        Renders a page to markdown
        :param page:
        :return:
        """
        self.num_index_stack = []
        return self.export_blocks(page.children)

    def image_export(self, caption: str, url: str):
        """
        make image file based on url and count.
        :param caption: image caption to use for filename
        :param url: url of image
        :return: image_path for the link in markdown
        """
        os.makedirs(self.image_dir, exist_ok=True)

        caption, _ = os.path.splitext(caption)
        filename = f'{caption}-{uuid.uuid4()}'

        r = requests.get(url, allow_redirects=True)
        content_type = r.headers['content-type']
        image_path = os.path.abspath(
            os.path.join(self.image_dir, f'{filename}{mimetypes.guess_extension(content_type)}')
        )
        with open(image_path, 'wb') as f:
            f.write(r.content)
        return image_path

    def preprocess_markdown(self, text: str) -> str:
        """
        Preprocesses the text
        :param text:
        :return:
        """
        text = text.replace('__', '**')
        text = text.replace('$$', '$')
        return text


def link_format(name, url):
    """
    make markdown link format string
    :param name:
    :param url:
    :return:
    """
    return f'[{name}]({url})'
