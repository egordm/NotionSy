from graphviz import Digraph

from notion_sync_tools.sync_tree import SyncNode


def draw_node(g: Digraph, node: SyncNode):
    notion_data = f'{node.metadata_notion.updated_at.strftime("%Y-%m-%d %H:%M")}|{node.metadata_notion.deleted}' \
        if node.metadata_notion else '-'
    local_data = f'{node.metadata_local.updated_at.strftime("%Y-%m-%d %H:%M")}|{node.metadata_local.deleted}' \
        if node.metadata_local else '-'

    g.node(
        name=node.unique_id,
        label=f'''
path: {node.metadata_local.path if node.metadata_local else '-'}
title: {node.metadata_notion.title if node.metadata_notion else '-'}
role: {node.node_role}
type: {node.node_type}
notion: {notion_data}
local: {local_data}
''',
        shape='box'
    )


def draw_tree(g: Digraph, node: SyncNode):
    draw_node(g, node)
    for child in node.children:
        draw_tree(g, child)
        g.edge(node.unique_id, child.unique_id)


def draw(tree: SyncNode):
    g = Digraph()
    draw_tree(g, tree)
    return g
