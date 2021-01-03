# NotionSy
A tool for bidirectional note synchronization to [Notion](https://www.notion.so/)

## Warning
The project is still in proof of concept stage.

## Usage
Create a configuration file specifying the sync directories: config.yml
```yaml
global:
  token_v2: ""

sync:
  notion_path: "notion page id"
  local_path: "local path"
```

Then you can use the sync by running command:
```bash
Usage: notionsy sync [OPTIONS]

Options:
  --config FILE       Read configuration from FILE.
  --token_v2 TEXT
  --notion_path TEXT
  --local_path TEXT
  --clean TEXT
  --help              Show this message and exit.
```

Example:
```bash
notionsy sync --config=./config.yml
```

## TODO
- [ ] Create file configuration for mapping specification
- [ ] Dry run option
- [ ] Backup before synchronization
- [ ] Documentation / Usage manual
- [ ] Tests