import asyncio
import logging

import click
from functools import wraps

import click_config_file
import yaml
from notion.client import NotionClient


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
    # Retrieve sorted lectures
    click.echo('Syncing')


if __name__ == "__main__":
    cli()
