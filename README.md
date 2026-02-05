# NetGalley Book Checker

A web scraper that finds highly-rated books on NetGalley and validates them on Goodreads.

## Features

- Scrapes book covers from NetGalley catalog (pages 1-5)
- Clicks covers to read title and author from side panels
- Cross-references books on Goodreads to get ratings
- Filters books by rating (4.0+) and excludes children's content
- Outputs results to TSV file for easy viewing in Excel
- Interactive HTML viewer to browse results

## Requirements

- Python 3.8+
- Conda environment: `goodreads`
- Playwright (for browser automation)
- Tabulate (for table formatting)

## Setup

1. Create conda environment:
```bash
conda create -n goodreads python=3.10
conda activate goodreads
```

2. Install dependencies:
```bash
pip install playwright tabulate
playwright install chromium
```

## Usage

Run the scraper:
```bash
python netgalley-checker.py
```

The script will:
1. Open a browser and navigate through NetGalley pages
2. Click on book covers and extract title/author info
3. Search each book on Goodreads for ratings and genres
4. Generate `netgalley_data.tsv` with results
5. Filter and sort by rating + popularity

## Viewing Results

Open `view.html` in a web browser to see the formatted results table (requires a local server):
```bash
python -m http.server 8000
```

Then visit `http://localhost:8000/view.html`

## How It Works

### NetGalley Scraping
- Finds detail rows with class `cover-table-detail-row`
- Gets preceding cover rows
- Clicks each cover to open side panel
- Reads title from `<h2 itemprop="name">` 
- Reads author from `<h3 itemprop="author">`
- Extracts NetGalley URL from corresponding detail row

### Goodreads Integration
- Searches for title + author
- Extracts rating, review count, and genres
- Deduplicates by URL to avoid processing same book twice

### Filtering
- Excludes books with rating < 4.0
- Excludes children's/YA books
- Sorts by (rating × review_count) for popularity

## Configuration

Edit the top of `netgalley-checker.py` to customize:
- `EXCLUDE_TAGS` - Genres to filter out
- `TARGET_GENRES` - Genres to prioritize (currently unused)

## Output

Generates `netgalley_data.tsv` with columns:
- Title
- Author
- Rating (Goodreads)
- Reviews (count)
- Genres
- NetGalley (link)
- GoodReads (link)
