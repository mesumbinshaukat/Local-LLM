# Plugins Guide

## Overview
MeAI supports custom Python plugins for extending functionality.

## Creating a Plugin
- Write a Python file with a function or class implementing your logic.
- Example:
  ```python
  def run(input_text):
      return f"Plugin received: {input_text}"
  ```
- Save your plugin in the `plugins/` directory.

## Installing Plugins
- Place your `.py` plugin file in the `plugins/` directory.
- The app will detect and list available plugins in the Plugins tab.

## Using Plugins
- Go to the Plugins tab in the desktop app.
- Select and run your plugin, providing any required input.
- Results will be shown in the UI.

## Best Practices
- Keep plugins stateless and secure.
- Validate and sanitize all input.
- Document your plugin's usage and expected input/output. 