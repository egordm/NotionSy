import asyncio
import logging
import os

import click
from functools import wraps

import click_config_file
import yaml
from notion.client import NotionClient

from notionsy.local_provider import LocalProvider
from notionsy.notion_provider import NotionProvider
from notionsy.sync_merger import SyncMerger
from notionsy.sync_planner import SyncPlanner, SyncConflictResolver, SyncActionTarget
from notionsy.syncer import Syncer
from notionsy.templates import university


def config_provider(file_path, cmd_name):
    if not os.path.exists(file_path):
        return {}

    with open(file_path) as config_data:
        config = yaml.full_load(config_data)
        return {
            **config['global'],
            **config[cmd_name]
        }


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@click.group()
@click.option('-v', '--verbose', count=True)
def cli(verbose):
    logging.basicConfig(level=logging.DEBUG if verbose > 0 else logging.INFO)
    pass


@cli.command()
@click_config_file.configuration_option(provider=config_provider, config_file_name='config.yml')
@click.option('--token_v2')
@click.option('--notion_path')
@click.option('--local_path')
@click.option('--clean', default=False)
@coro
async def sync(token_v2, notion_path, local_path, clean):
    client = NotionClient(token_v2=token_v2)
    model = university.build_config(local_path, notion_path, client)
    data = model.data()
    data.read()

    local_provider = LocalProvider(model)
    local_provider.fetch_tree(data.local_tree)
    notion_provider = NotionProvider(client, model)
    notion_provider.fetch_tree(data.notion_tree)

    merger = SyncMerger()
    merged_tree = merger.merge_nodes(model.hierarchy, data.local_tree, data.notion_tree)

    planner = SyncPlanner()
    plan = planner.plan(merged_tree)
    resolver = SyncConflictResolver()
    plan = resolver.resolve(plan)
    logging.info('============== SYNC PLAN ===============')
    for a in plan:
        logging.info(a)
    logging.info('============ END SYNC PLAN =============')

    syncer = Syncer({
        SyncActionTarget.LOCAL: local_provider,
        SyncActionTarget.NOTION: notion_provider
    })
    syncer.sync(plan)

    data.apply(merged_tree)
    data.write()


if __name__ == "__main__":
    cli()
