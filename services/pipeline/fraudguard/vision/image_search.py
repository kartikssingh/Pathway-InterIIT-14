"""Reverse / keyword image search over the Google Custom Search API.

Used by :mod:`fraudguard.vision.face_matching` to find public photographs of a
KYC applicant so their face can be matched against the form.

Two things changed from the original ``gis_demo.py``:

* the constructor called ``sys.exit(1)`` when credentials were missing — a
  library that kills the interpreter, which took the whole Pathway worker down.
  It raises :class:`~fraudguard.errors.ConfigurationError` now.
* it read ``GOOGLE_CLOUD_API_KEY_2`` together with
  ``PROGRAMMABLE_SEARCH_ENGINE_ID_1`` — a mismatched pair. Credentials come from
  the shared key pool, so key *n* is always used with engine *n*.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import requests

from fraudguard.errors import ConfigurationError
from fraudguard.logging import get_logger

logger = get_logger("fraudguard.vision.image_search")


def _out_dir() -> Path:
    from fraudguard.config import get_settings

    return get_settings().paths.out


class GoogleImageSearchFinder:
    def __init__(self, download_dir='input'):
        from google_images_search import GoogleImagesSearch

        from fraudguard.enrichment.search import SearchKeyPool

        pool = SearchKeyPool.from_settings()
        key = pool.next_key()
        if key is None:
            raise ConfigurationError(
                "Image search needs a matching GOOGLE_CLOUD_API_KEY_n / "
                "PROGRAMMABLE_SEARCH_ENGINE_ID_n pair in .env"
            )

        # Setup download directory
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Image download directory: %s", self.download_dir.absolute())

        try:
            self.gis = GoogleImagesSearch(key.api_key, key.engine_id)
        except Exception as exc:
            raise ConfigurationError(f"Could not initialise Google Images Search: {exc}") from exc
        logger.info("Connected to the Google Images Search API")

    def find_similar_images(self, image_path, num_results=10):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        print(f"\nAnalyzing image: {image_path}")

        results = {
            'search_results': [],
            'query_metadata': {
                'image_path': str(image_path),
                'num_results': num_results
            }
        }

        try:
            self.gis.search({'num': num_results}, path_to_dir=None)
            
            for image in self.gis.results():
                results['search_results'].append({
                    'url': image.url,
                    'referrer_url': getattr(image, 'referrer_url', None),
                    'width': getattr(image, 'width', None),
                    'height': getattr(image, 'height', None),
                    'filesize': getattr(image, 'filesize', None),
                    'format': getattr(image, 'format', None)
                })
        except Exception as e:
            print(f"Search error: {e}")
            raise

        return results

    def search_by_keyword(self, keyword, num_results=10):
        print(f"\nSearching for: {keyword}")

        results = {
            'search_results': [],
            'query_metadata': {
                'keyword': keyword,
                'num_results': num_results
            }
        }

        try:
            search_params = {
                'q': keyword,
                'num': num_results,
                'safe': 'off',
                'fileType': 'jpg|png|gif',
                'imgType': 'photo'
            }
            
            self.gis.search(search_params)
            
            for image in self.gis.results():
                results['search_results'].append({
                    'url': image.url,
                    'referrer_url': getattr(image, 'referrer_url', None),
                    'width': getattr(image, 'width', None),
                    'height': getattr(image, 'height', None),
                    'title': getattr(image, 'title', 'N/A'),
                    'filesize': getattr(image, 'filesize', None),
                    'format': getattr(image, 'format', None)
                })
        except Exception as e:
            print(f"Search error: {e}")
            raise

        return results

    def reverse_image_search(self, image_path, num_results=10):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        print(f"\nPerforming reverse image search: {image_path}")

        results = {
            'search_results': [],
            'query_metadata': {
                'image_path': str(image_path),
                'num_results': num_results,
                'search_type': 'reverse_image'
            }
        }

        try:
            self.gis.search({'num': num_results}, path_to_dir=None)
            
            for image in self.gis.results():
                results['search_results'].append({
                    'url': image.url,
                    'referrer_url': getattr(image, 'referrer_url', None),
                    'width': getattr(image, 'width', None),
                    'height': getattr(image, 'height', None),
                    'filesize': getattr(image, 'filesize', None),
                    'format': getattr(image, 'format', None)
                })
        except Exception as e:
            print(f"Reverse search error: {e}")
            raise

        return results

    def display_results(self, results):
        print("\n" + "="*80)
        print("SEARCH RESULTS")
        print("="*80)

        if 'query_metadata' in results:
            print("\nQuery Information:")
            for key, value in results['query_metadata'].items():
                print(f"  - {key}: {value}")

        if results['search_results']:
            print(f"\nFound {len(results['search_results'])} images:")
            for i, img in enumerate(results['search_results'], 1):
                print(f"\n  {i}. Image URL: {img['url']}")
                if img.get('referrer_url'):
                    print(f"     Source Page: {img['referrer_url']}")
                if img.get('title'):
                    print(f"     Title: {img['title']}")
                if img.get('width') and img.get('height'):
                    print(f"     Dimensions: {img['width']}x{img['height']}")
                if img.get('format'):
                    print(f"     Format: {img['format']}")
        else:
            print("\nNo results found.")

        print("\n" + "="*80)

    def download_images(self, results):
        """Download all images from search results to the input folder."""
        print("\n" + "="*80)
        print("DOWNLOADING IMAGES")
        print("="*80)
        
        downloaded_count = 0
        failed_count = 0
        downloaded_files = []
        
        for i, img in enumerate(results['search_results'], 1):
            try:
                url = img['url']
                print(f"\nDownloading {i}/{len(results['search_results'])}: {url}")
                
                # Get file extension from URL or use default
                parsed_url = urlparse(url)
                ext = Path(parsed_url.path).suffix
                if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    ext = '.jpg'
                
                # Create filename
                filename = f"image_{i:03d}{ext}"
                filepath = self.download_dir / filename
                
                # Download image with timeout
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                
                # Save image
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                downloaded_count += 1
                downloaded_files.append(str(filepath))
                print(f"  ✓ Saved to: {filepath}")
                
            except Exception as e:
                failed_count += 1
                print(f"  ✗ Failed: {e}")
        
        print("\n" + "="*80)
        print(f"Download complete: {downloaded_count} succeeded, {failed_count} failed")
        print(f"Images saved to: {self.download_dir.absolute()}")
        print("="*80)
        
        return {
            'downloaded_count': downloaded_count,
            'failed_count': failed_count,
            'downloaded_files': downloaded_files
        }


def main():
    finder = GoogleImageSearchFinder()
    current_dir = Path(__file__).parent

    image_path = current_dir / "WhatsApp Image 2025-11-29 at 11.39.22.jpeg"
    
    if not image_path.exists():
        print(f"\nImage not found: {image_path}")
        print("\nExample usage:")
        print("  finder = GoogleImageSearchFinder()")
        print("  results = finder.search_by_keyword('sunset beach')")
        print("  finder.display_results(results)")
        return

    print(f"\nUsing image: {image_path.name}")
    
    search_keyword = input("\nEnter search keyword (or press Enter to skip keyword search): ").strip()

    try:
        if search_keyword:
            results = finder.search_by_keyword(search_keyword, num_results=10)
        else:
            print("\nNote: Google Custom Search API doesn't support direct reverse image search.")
            print("Performing keyword-based search instead.")
            print("For reverse image search, use cloud_vision_demo.py")
            default_keyword = "landscape photography"
            print(f"Using default keyword: {default_keyword}")
            results = finder.search_by_keyword(default_keyword, num_results=10)
        
        finder.display_results(results)

        output_file = _out_dir() / 'google_image_search_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nFull results saved to: {output_file}")
        
        # Download images
        download_stats = finder.download_images(results)
        
        # Add download stats to results
        results['download_stats'] = download_stats
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()