import asyncio
import logging

import click
from functools import wraps

import click_config_file
import yaml
from notion.client import NotionClient

from notion_sync_tools.sync import NotionProvider, RecurseMode
from notion_sync_tools.syncs import UniversitySync


def config_provider(file_path, cmd_name):
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
def cli():
    logging.basicConfig(level=logging.DEBUG)
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
    provider = NotionProvider(client, notion_path)
    sync = UniversitySync(provider, local_path)

    courses = list(sync.iter_courses())
    u = 0

    res = provider.root.children[1].views[0].build_query(
        sort=[{"direction": "descending", "property": "updated"}],
        filter={"filters": [
            {
                "filter": {
                    "operator": "date_is_after",
                    "value": {
                        "type": "exact",
                        "value": {
                            "start_date": "2020-11-21",
                            "type": "datetime"
                        }
                    }
                },
                "property": "hPH="
            }
        ], "operator": "and"}
    ).execute()
    # Retrieve sorted lectures

    tree = sync.downsync()

    click.echo('Syncing')


if __name__ == "__main__":
    cli()
