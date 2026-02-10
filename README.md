# AI Dev Tools

A collection of tools for AI-assisted development with Claude Code.

## Tools

### [Asana](./asana/)

Direct REST API client for Asana task management. Reliable 30-second timeouts, automatic retries.

```bash
# Install
cd asana && ./setup.sh

# Use
asana my-tasks -i
```

[Full documentation](./asana/README.md)

### [Letta](./letta/)

Persistent memory system for Claude Code using Letta Cloud. Remember learnings across sessions.

```bash
# Install
cd letta && ./install.sh

# Configure
echo "LETTA_API_KEY=your_key" > ~/.claude/hooks/letta/.env
```

[Full documentation](./letta/README.md)

## Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/your-org/ai-dev-tools.git
   ```

2. Set up the tools you need:
   - For Asana: `cd asana && ./setup.sh` and set `ASANA_ACCESS_TOKEN`
   - For Letta: Run `./letta/install.sh` and set `LETTA_API_KEY`

## Structure

```
ai-dev-tools/
├── asana/                  # Asana CLI tool
│   ├── asana_client.py     # Main client (CLI & library)
│   ├── bin/asana           # CLI wrapper script
│   ├── setup.sh            # Installer (venv + ~/bin symlink)
│   ├── README.md           # Documentation
│   └── SETUP.md            # Setup guide
├── letta/                  # Letta memory hooks
│   ├── hooks/              # Hook scripts
│   ├── templates/          # Config templates
│   ├── install.sh          # Installer
│   ├── README.md           # Documentation
│   └── SETUP.md            # Setup guide
├── README.md               # This file
├── CLAUDE.md               # Guidelines for Claude
└── LICENSE                 # MIT License
```

## Contributing

1. Follow existing code patterns
2. Add documentation for new features
3. Test changes before submitting
4. Keep tools self-contained (minimal dependencies)

## License

MIT
