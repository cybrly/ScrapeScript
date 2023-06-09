# ScrapeScript

Domain email scraper that "just works." Used for red team and pentesting scenarios; educational purposes only.

For many local government and K-12 school websites, their staff email directories are loosly obfuscated wit a ROT13 cipher to "prevent" email scraping. This script will convert those ROT13 encoded emails to plaintext before printing to stdout.

# Installation

```
git clone https://github.com/cybrly/ScrapeScript.git
cd ScrapeScript
python3 -m venv venv
source venv/bin/activate
python3 scrapescript.py
```

# Usage

```
python3 scrapescript.py domain.com
```

# Demo


[![asciicast](https://asciinema.org/a/590597.svg)](https://asciinema.org/a/590597)
