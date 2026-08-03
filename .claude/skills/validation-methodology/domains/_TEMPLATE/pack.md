# Domain Pack — manifest

<!-- Copy the whole _TEMPLATE/ folder, rename it in kebab-case (e.g. my-domain, maya-fx),
     and fill this file. A pack only adds domain knowledge + trusted sources to the core.
     By convention the sources live in sources.md and the knowledge in knowledge.md
     (fixed names — the core loads them when the pack applies). -->

- **pack_name:** <kebab-case, matches the folder name>
- **description:** <what domain this covers and when to load it>
- **test_execution:** <human | auto>
  <!-- human: a person runs the test (e.g. open a GUI app, check a render).
       auto:  Claude Code can run it (e.g. code/scripts) → may use the test-runner agent. -->
- **version_pins:** <software + versions this pack targets, e.g. engine build / pinned patch>

## Optional
- **custom_agents:** <pack-specific subagents in this pack's agents/ folder, if any>
- **maintainer / notes:** <anything a new user must know>
