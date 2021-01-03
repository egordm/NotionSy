from graphviz import Digraph

from notion_sync_tools.sync_tree import SyncNode


def draw_node(g: Digraph, node: SyncNode):
    g.node(
        name=str(node.id),
        label=f'''
id: {node.id}
role: {node.node_role}
type: {node.node_type}
synced_at: {node.synced_at.strftime("%Y-%m-%d %H:%M") if node.synced_at else None}
changed: {node.changed()}
notion: {node.metadata_notion}
local: {node.metadata_local}
''',
        shape='box'
    )


def draw_tree(g: Digraph, node: SyncNode):
    draw_node(g, node)
    for child in node.children:
        draw_tree(g, child)
        g.edge(str(node.id), str(child.id))


def draw(tree: SyncNode):
    g = Digraph()
    draw_tree(g, tree)
    return g
