# Suggested Agent Instructions

Add guidance like this to the agent configuration that uses Puppet MCP:

## Puppet behavior

- Call `list_expressions` before choosing an affect, and use only expressions
  returned for the configured puppet.
- Call `set_expression` for meaningful response or conversational changes, not
  for every token, sentence, or internal tool step.
- Supply intensity only in the inclusive range `[0.0, 1.0]`. It is retained as
  state but does not blend the current static Tk PNGs.
- Do not invent expression names or silently substitute `idle`.
- Treat puppet tool failures as non-blocking: continue the core task and avoid
  repeatedly retrying an unavailable renderer.
- Choose chibi or saki with `PUPPET_MCP_PUPPET` in MCP registration. Runtime
  puppet switching is not available.

Each server instance controls one window and has process-local state. Multiple
registered instances create multiple windows.