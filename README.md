# NetGalley Book Checker

A web scraper that finds highly-rated, most requested books on NetGalley and cross-references them on Goodreads.
View at: https://pot0to.github.io/netgalley-checker/view.html

## Features
- Scrapes book covers from NetGalley Most Requested catalog (pages 1-5)
- Cross-references books on Goodreads to get ratings
- Filters books by rating (4.0+) and excludes children's content

## Requirements
- Python 3.8+
- Conda environment: `goodreads`
- Playwright (for browser automation)
- Tabulate (for table formatting)
