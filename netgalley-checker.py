import asyncio
from playwright.async_api import async_playwright
import urllib.parse
from tabulate import tabulate
import re

# Configuration
USER_DATA_DIR = "./netgalley_session"
EXCLUDE_TAGS = ["children", "teen", "middle grade", "ya", "young adult"]
TARGET_GENRES = ["sci-fi", "fantasy", "science fiction"]

# Initialize this at the start of your run_scraper() function:
# visited_urls = set()

async def add_goodreads_data(page, book_info, visited_urls):
    title = book_info["title"]
    author = book_info["author"]
    try:
        search_query = f"{title} {author}" if author else title
        search_url = f"https://www.goodreads.com/search?q={urllib.parse.quote(search_query)}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        
        # 1. Search Result Check
        results_header = page.locator("text=/Page 1 of about/i")
        await results_header.wait_for(state="visible", timeout=10000)

        # 2. Duplicate Check & URL Capture
        first_result = page.locator("a.bookTitle").first
        if await first_result.count() == 0: return None
        
        gr_url = f"https://www.goodreads.com{await first_result.get_attribute('href')}"
        book_info["gr_url"] = gr_url
        if gr_url in visited_urls:
            return None
        visited_urls.add(gr_url)

        # 3. Scrape Page
        await first_result.click()
        await page.wait_for_load_state("domcontentloaded")

        # Basic Stats
        rating_el = page.locator(".RatingStatistics__rating").first
        count_el = page.locator('[data-testid="ratingsCount"]').first
        author_el = page.locator(".ContributorLink__name").first

        author = (await author_el.inner_text()).strip() if await author_el.count() > 0 else "Unknown"
        book_info["author"] = author

        rating = float(await rating_el.inner_text()) if await rating_el.count() > 0 else 0.0
        book_info["rating"] = rating

        count = int(re.sub(r'\D', '', await count_el.inner_text())) if await count_el.count() > 0 else 0
        book_info["count"] = count

        # 4. Genre Handling
        genre_container = page.locator('.BookPageMetadataSection__genres')
        await genre_container.scroll_into_view_if_needed()
        
        more_btn = page.locator("button:has-text('more'), .Button--link:has-text('more')").first
        if await more_btn.is_visible():
            await more_btn.click()
            await asyncio.sleep(0.5)

        genre_elements = genre_container.locator('.Button__labelItem')
        try:
            await genre_elements.first.wait_for(state="visible", timeout=5000)
        except: pass
        
        genre_list = await genre_elements.all_inner_texts()
        
        # Remove "...more" entries
        genre_list = [g for g in genre_list if g.strip() != "...more"]

        book_info["genres"] = ", ".join(genre_list)

    except Exception as e:
        print(f"⚠️ Error with {title}: {e}")

async def run_scraper():
    async with async_playwright() as p:
        visited_titles = set() 
        visited_urls = set()   
        final_results = [] 

        context = await p.chromium.launch_persistent_context(USER_DATA_DIR, headless=False)
        page = await context.new_page()

        books_to_process = []

        # 1. NETGALLEY SCANNING (PAGES 1-5)
        for p_num in range(1, 6):
            print(f"\n🚀 Navigating to NetGalley Page {p_num}...")
            url = f"https://www.netgalley.com/catalog/category/36/mostRequested?=s.requestsRecent&direction=desc&page={p_num}"
            await page.goto(url, wait_until="networkidle")

            # Find all detail rows (tr with cover-table-detail-row class)
            # Then get the preceding cover row to avoid picking up navbar rows
            detail_rows = page.locator('tr.cover-table-detail-row')
            detail_count = 0
            # Filter to only visible rows
            for idx in range(await detail_rows.count()):
                if await detail_rows.nth(idx).is_visible():
                    detail_count += 1
            
            for detail_idx in range(detail_count):
                detail_row = detail_rows.nth(detail_idx)
                cover_row = detail_row.locator('xpath=preceding-sibling::tr[1]').first
                
                # Get all covers in this row
                cover_links_in_row = cover_row.locator('a')
                covers_in_row = await cover_links_in_row.count()
                
                # Get all detail links in the corresponding detail row
                detail_links_in_row = detail_row.locator('a')
                
                for col in range(covers_in_row):
                    try:
                        cover_link = cover_links_in_row.nth(col)
                        detail_link = detail_links_in_row.nth(col)
                        
                        # Scroll cover into view if necessary
                        await cover_link.scroll_into_view_if_needed()
                        
                        # Click on the cover to open side panel
                        await cover_link.click()

                        # Wait for panel to open
                        for retry in range(3):
                            close_buttons = page.locator('button[class*="close-button"]')
                            close_count = await close_buttons.count()
                            for cb_idx in range(close_count):
                                btn = close_buttons.nth(cb_idx)
                                if await btn.is_visible():
                                    break
                            await asyncio.sleep(0.5)
                        
                        # Read title and author from side panel
                        title_els = page.locator('h2[itemprop="name"]')
                        author_els = page.locator('h3[itemprop="author"]')
                        
                        # Get all visible elements and take the first one
                        title = ""
                        title_count = await title_els.count()
                        for idx in range(title_count):
                            el = title_els.nth(idx)
                            if await el.is_visible():
                                title = (await el.inner_text()).strip()
                                break
                        
                        author = ""
                        author_count = await author_els.count()
                        for idx in range(author_count):
                            el = author_els.nth(idx)
                            if await el.is_visible():
                                author = (await el.inner_text()).strip()
                                break
                        
                        # Remove "by " prefix if present
                        if author.lower().startswith("by "):
                            author = author[3:].strip()
                        ng_url = f"https://www.netgalley.com{await detail_link.get_attribute('href')}" if await detail_link.get_attribute('href') else ""
                        
                        if title and title not in visited_titles:
                            book_info = {
                                "title": title,
                                "ng_url": ng_url,
                                "author": author,
                                "rating": 0.0,
                                "count": 0,
                                "genres": "",
                                "gr_url": ""
                            }
                            books_to_process.append(book_info)
                            visited_titles.add(title)
                            print(f"📖 Found: {title} by {author}")
                    except Exception as e:
                        print(f"⚠️ Error processing cover {row},{col}: {e}")
                    finally:
                        # Close the side panel by clicking the first visible close button
                        # Retry up to 3 times as the panel can load slowly
                        for retry in range(3):
                            close_buttons = page.locator('button[class*="close-button"]')
                            close_count = await close_buttons.count()
                            for cb_idx in range(close_count):
                                btn = close_buttons.nth(cb_idx)
                                if await btn.is_visible():
                                    try:
                                        await btn.click()
                                    except:
                                        pass
                                    break
                            await asyncio.sleep(0.5)
                        await asyncio.sleep(0.3)

        # 2. GOODREADS CROSS-REFERENCING
        print(f"\n📚 Found {len(books_to_process)} unique books. Starting Goodreads analysis...")

        for book_info in books_to_process:
            # add_goodreads_data updates book_info in-place or returns None if filtered/duplicate
            await add_goodreads_data(page, book_info, visited_urls)
            final_results.append(book_info)
            print(f"✅ Verified: {book_info['title']} ({book_info['rating']}⭐)")

            await asyncio.sleep(1.5)

        # 3. FILTERING & SORTING
        # --- FILTERING, SORTING, AND OUTPUT ---
        if final_results:
            # 1. Apply Rating and Genre Filter
            bad_genres = {"children", "middle grade", "teen", "young adult", "childrens"}
            filtered = [
                b for b in final_results 
                if b['rating'] >= 4.0 and 
                not any(genre.lower() in bad_genres for genre in b['genres'].split(", "))
            ]

            if not filtered:
                print("\n⚠️ No books met the 4.0+ rating criteria.")
            else:
                # 2. Sort by Popularity
                filtered.sort(key=lambda x: x['rating'] * x['count'], reverse=True)

                # 3. PRETTY PRINT TO CONSOLE
                # Use a simplified list for the terminal to keep it narrow
                console_data = [
                    [d["title"][:40], d["author"][:20], d["rating"], f"{d['count']:,}", d["genres"]] 
                    for d in filtered
                ]
                headers = ["Title", "Author", "Rating", "Reviews", "Genres"]
                print(f"\n🏆 Found {len(filtered)} matches (4.0+ Rating):")
                print(tabulate(console_data, headers=headers, tablefmt="fancy_grid"))

                # 4. WRITE TAB-SEPARATED TO FILE
                # TSV is great because you can copy-paste directly into Excel
                filename = "netgalley_data.tsv"
                with open(filename, "w", encoding="utf-8") as f:
                    # Write Header
                    file_headers = ["Title", "Author", "Rating", "Reviews", "Genres", "NetGalley", "GoodReads"]
                    f.write("\t".join(file_headers) + "\n")
                    
                    # Write Rows
                    for b in filtered:
                        row = [
                            str(b['title']),
                            str(b['author']),
                            str(b['rating']),
                            str(b['count']),
                            str(b['genres']),
                            str(b['ng_url']),
                            str(b['gr_url'])
                        ]
                        f.write("\t".join(row) + "\n")
                
                print(f"\n💾 TSV data successfully saved to: {filename}")
        else:
            print("\nNo books were processed.")

        await context.close()

if __name__ == "__main__":
    asyncio.run(run_scraper())