# Craft Product Share Button Hotfix

This update fixes Craft product Share buttons that did nothing because product names were inserted directly inside inline `onclick` attributes, which could break the HTML/JavaScript attribute quoting.

## Fix
- Craft product cards now use safe `data-share-title` and `data-share-url` attributes.
- Craft product detail Share uses the same safe data attributes.
- Craft Admin product Share is fixed too.
- A delegated click handler in `templates/craft/base.html` opens the Macleen's share dialog.
- A copy-link fallback is provided if the share helper script fails to load.
- Share helper cache version was bumped to `v=3` so browsers fetch the current script.
