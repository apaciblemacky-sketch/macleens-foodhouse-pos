# Share Dialog Windows Hotfix

The previous build called the browser/OS Web Share API directly. On some Windows/Edge installations, the Windows share sheet opens but reports that it cannot show available share targets.

This update replaces the primary Share action with a built-in Macleen's share dialog for Food House, Food products, Craft Shop, and Craft products. It offers Facebook, WhatsApp, Telegram, Email, and Copy Link. On mobile devices that support Web Share, a separate **More Apps…** button is available. Desktop Windows no longer invokes the failing system share sheet by default.
