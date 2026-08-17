"""Face similarity search over images found for a KYC applicant.

Given the face crops taken from a KYC form, this:

1. builds a FAISS index of their DeepFace embeddings,
2. searches the web for images of the applicant by name,
3. matches the downloaded images against the index,
4. returns the source page URLs of the images that matched.

Those URLs feed back into the adverse-media analysis as extra evidence.

``deepface``, ``faiss`` and ``opencv`` are heavy optional dependencies; they are
imported lazily by :func:`match_faces_to_sources` so importing this module (or
the package) never pulls in TensorFlow.

Usage::

    from fraudguard.vision.face_matching import CustomPathwayWorkflow

    workflow = CustomPathwayWorkflow(face_image_paths=["/tmp/face_1.jpg"])
    source_urls = workflow.run(input_folder="input", search_keyword="Jane Doe")
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from fraudguard.vision.image_search import GoogleImageSearchFinder

logger = logging.getLogger("fraudguard.vision.face_matching")


def _out_dir() -> Path:
    from fraudguard.config import get_settings

    return get_settings().paths.out


def _deepface():
    """Import DeepFace on first use (it drags in TensorFlow)."""
    from deepface import DeepFace

    return DeepFace


def _faiss():
    import faiss

    return faiss

class CustomPathwayWorkflow:
    """
    Custom workflow that builds face database from a list of file paths
    and performs similarity search, returning source page URLs.
    """
    
    def __init__(
        self,
        face_image_paths: List[str],
        temp_index_path: str = "temp_face_index.faiss",
        temp_paths_json: str = "temp_image_paths.json",
        temp_names_json: str = "temp_face_names.json",
        output_folder: str = "output"
    ):
        """
        Initialize the custom workflow.
        
        Args:
            face_image_paths: List of absolute paths to face images
            temp_index_path: Temporary path for FAISS index
            temp_paths_json: Temporary path for image paths JSON
            temp_names_json: Temporary path for face names JSON
            output_folder: Folder to save results
            metadata_path: Path to search metadata JSON (for source URLs)
        """
        self.face_image_paths = face_image_paths
        self.temp_index_path = temp_index_path
        self.temp_paths_json = temp_paths_json
        self.temp_names_json = temp_names_json
        self.output_folder = output_folder
        
        self.metadata_path = _out_dir() / "google_image_search_results.json"
        self.input_files = []
        self.output_files = []
        
        # Validate paths
        self._validate_paths()
        
        # Create output folder
        Path(output_folder).mkdir(exist_ok=True)
        
        logger.info("="*80)
        logger.info("CUSTOM PATHWAY WORKFLOW - INITIALIZING")
        logger.info("="*80)
        logger.info(f"Face images to process: {len(face_image_paths)}")
        logger.info(f"Output folder: {Path(output_folder).absolute()}")
    
    def _validate_paths(self):
        """Validate that all face image paths exist."""
        invalid_paths = []
        for path in self.face_image_paths:
            if not os.path.exists(path):
                invalid_paths.append(path)
        
        if invalid_paths:
            logger.error("The following paths do not exist:")
            for path in invalid_paths:
                logger.error(f"  - {path}")
            raise FileNotFoundError(f"{len(invalid_paths)} face image paths not found")
        
        logger.info(f"OK All {len(self.face_image_paths)} face image paths validated")
    
    def _extract_person_name(self, file_path: str) -> str:
        """
        Extract person name from filename.
        
        Example: 'john_doe.jpg' → 'John Doe'
        """
        filename = Path(file_path).stem
        return filename.replace('_', ' ').title()
    
    def _get_face_embedding(self, image_path: str) -> Optional[np.ndarray]:
        """
        Extract face embedding using DeepFace.
        
        Args:
            image_path: Path to image file
            
        Returns:
            512-dimensional embedding vector or None if no face detected
        """
        try:
            logger.info(f"Input face image paths: {image_path}")
            embeddings = _deepface().represent(
                img_path=image_path,
                model_name="Facenet512",
                enforce_detection=True,
                detector_backend="opencv"
            )
            embedding = np.array(embeddings[0]["embedding"], dtype=np.float32)
            logger.info(f"  OK Processed: {Path(image_path).name}")
            return embedding
            
        except Exception as e:
            logger.warning(f"  FAILED No face detected in {Path(image_path).name}")
            return None
    
    def build_face_database(self) -> bool:
        """
        Build FAISS index from the provided list of face image paths.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "="*80)
        logger.info("STEP 1: BUILDING FACE DATABASE")
        logger.info("="*80)
        
        embeddings = []
        valid_paths = []
        face_names = {}
        
        logger.info(f"\nProcessing {len(self.face_image_paths)} face images...\n")
        
        # Process each image
        for img_path in self.face_image_paths:
            embedding = self._get_face_embedding(img_path)
            
            if embedding is not None:
                embeddings.append(embedding)
                valid_paths.append(img_path)
                
                # Extract person name
                person_name = self._extract_person_name(img_path)
                face_names[img_path] = person_name
        
        if not embeddings:
            logger.error("\nERROR No faces detected in any images!")
            return False
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        logger.info(f"\nOK Successfully processed {len(embeddings)} faces")
        logger.info(f"OK Skipped {len(self.face_image_paths) - len(embeddings)} images (no face detected)")
        
        # Build FAISS index
        logger.info("\nBuilding FAISS index...")
        dimension = embeddings_array.shape[1]
        faiss = _faiss()
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)
        
        # Save index
        faiss.write_index(index, self.temp_index_path)
        logger.info(f"OK Saved FAISS index to: {self.temp_index_path}")
        
        # Save image paths
        with open(self.temp_paths_json, 'w') as f:
            json.dump(valid_paths, f, indent=2)
        logger.info(f"OK Saved image paths to: {self.temp_paths_json}")
        
        # Save face names
        with open(self.temp_names_json, 'w') as f:
            json.dump(face_names, f, indent=2)
        logger.info(f"OK Saved face names to: {self.temp_names_json}")
        
        # Display mapping
        logger.info("\nFace to Name Mapping:")
        for path, name in face_names.items():
            logger.info(f"  - {Path(path).name} → {name}")
        
        return True
    
    def _load_metadata(self) -> Dict:
        """Load search metadata if available."""
        metadata = {}
        
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'r') as f:
                    search_data = json.load(f)
                
                self.input_files = []
                # Create mapping of downloaded files to their URLs
                if 'download_stats' in search_data and 'downloaded_files' in search_data['download_stats']:
                    downloaded_files = search_data['download_stats']['downloaded_files']
                    search_results = search_data.get('search_results', [])
                    
                    for i, file_path in enumerate(downloaded_files):
                        if i < len(search_results):
                            metadata[Path(file_path).name] = search_results[i]
                            self.input_files.append(Path(file_path))

                logger.info(f"OK Loaded metadata for {len(metadata)} images")
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")
        
        return metadata
    
    def _find_similar_face(
        self, 
        query_embedding: np.ndarray, 
        index: "object",
        image_paths: List[str],
        face_names: Dict[str, str],
        top_k: int = 1
    ) -> List[Dict]:
        """
        Find top K similar faces from database.
        
        Args:
            query_embedding: Query face embedding
            index: FAISS index
            image_paths: List of database image paths
            face_names: Dictionary of face names
            top_k: Number of matches to return
            
        Returns:
            List of match dictionaries with face info and similarity
        """
        # Search FAISS index
        query_emb = query_embedding.reshape(1, -1).astype('float32')
        distances, indices = index.search(query_emb, top_k)
        
        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            match_path = image_paths[idx]
            person_name = face_names.get(match_path, Path(match_path).stem)
            
            # Calculate similarity score (inverse of distance)
            similarity_score = max(0, min(100, 100 - (dist / 10)))
            
            results.append({
                "image": match_path,
                "person_name": person_name,
                "distance": float(dist),
                "similarity_score": round(similarity_score, 2)
            })
        
        return results
    
    def perform_similarity_search(self, input_folder: str) -> List[Dict]:
        """
        Perform face similarity search on images in input folder.
        
        Args:
            input_folder: Folder containing query images
            
        Returns:
            List of result dictionaries
        """
        logger.info("\n" + "="*80)
        logger.info("STEP 2: FACE SIMILARITY SEARCH")
        logger.info("="*80)
        
        # Load database
        logger.info("\nLoading face database...")
        index = _faiss().read_index(self.temp_index_path)
        
        with open(self.temp_paths_json, 'r') as f:
            image_paths = json.load(f)
        
        with open(self.temp_names_json, 'r') as f:
            face_names = json.load(f)
        
        logger.info(f"OK Loaded database with {len(image_paths)} faces")
        
        # Load metadata
        metadata = self._load_metadata()
        
        # Get all images from input folder
        input_path = Path(input_folder)
        if not input_path.exists():
            logger.error(f"ERROR Input folder not found: {input_folder}")
            return []

        all_items = list(input_path.iterdir())
        logger.info(f"DEBUG: All items in {input_folder}: {[str(f) for f in all_items]}")
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        image_files = sorted([
            f for f in input_path.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ])
        
        if not image_files:
            logger.warning(f"No images found in {input_folder}/")
            return []
        
        logger.info(f"Found {len(image_files)} images to process\n")
        
        # Process each image
        all_results = []
        processed_count = 0
        skipped_count = 0
        
        for img_file in image_files:
            logger.info(f"[PROCESSING] {img_file.name}")
            
            # Extract embedding
            query_embedding = self._get_face_embedding(str(img_file))
            if query_embedding is None:
                logger.warning(f"  [SKIPPED] No face detected")
                skipped_count += 1
                continue
            
            # Find best match
            matches = self._find_similar_face(
                query_embedding, index, image_paths, face_names, top_k=1
            )
            if not matches:
                skipped_count += 1
                continue
            
            best_match = matches[0]
            
            # Copy query image to output
            output_path = Path(self.output_folder) / img_file.name
            shutil.copy2(img_file, output_path)
            self.output_files.append(output_path)
            # Build result
            result = {
                "query_image": img_file.name,
                "query_image_path": str(output_path),
                "most_similar_person": best_match["person_name"],
                "similarity_score": best_match["similarity_score"],
                "distance": best_match["distance"],
                "timestamp": datetime.now().isoformat()
            }
            
            # Add metadata if available
            if img_file.name in metadata:
                result["source_url"] = metadata[img_file.name].get('url')
                result["source_page"] = metadata[img_file.name].get('referrer_url')
            
            logger.info(f"  [MATCH] {best_match['person_name']} "
                       f"(similarity: {best_match['similarity_score']:.1f}%, "
                       f"distance: {best_match['distance']:.2f})")
            
            all_results.append(result)
            processed_count += 1
        
        # Save results
        results_file = _out_dir() / "similarity_results.json"
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("PROCESSING COMPLETE")
        logger.info("="*80)
        logger.info(f"OK Processed: {processed_count} images")
        logger.info(f"OK Skipped: {skipped_count} images (no face detected)")
        logger.info(f"OK Total: {len(image_files)} images")
        
        if all_results:
            logger.info(f"\n[RESULTS]")
            for result in all_results:
                logger.info(f"  {result['query_image']}: "
                          f"{result['most_similar_person']} "
                          f"({result['similarity_score']}% similar)")
        
        logger.info(f"\nOK Results saved to: {results_file}")
        
        return all_results
    
    def cleanup_temp_files(self):
        """Remove temporary database files."""
        temp_files = [
            self.temp_index_path,
            self.temp_paths_json,
            self.temp_names_json
        ]
        temp_files.extend([str(f) for f in self.input_files])
        temp_files.extend([str(f) for f in self.output_files])
        
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.info(f"Removed temporary file: {temp_file}")
    
    def run(
        self, 
        input_folder: str = "input",
        cleanup: bool = True,
        search_keyword: str | None = None,
        num_results: int = 10
    ) -> List[str]:
        """
        Run the complete workflow and return source page URLs.
        
        Args:
            input_folder: Folder containing query images
            cleanup: Whether to remove temporary files after processing
            
        Returns:
            List of source page URLs from the similarity search results
        """
        logger.info("="*80)
        logger.info("CUSTOM PATHWAY WORKFLOW - STARTING")
        logger.info("="*80)
        
        try:
            # Step 1: Build face database from provided paths
            if not self.build_face_database():
                logger.error("\nERROR Failed to build face database")
                return []
            
            # Optional Step: Google Image Search to populate metadata for source URLs
            if search_keyword:
                logger.info("\n" + "="*80)
                logger.info("STEP 1.5: GOOGLE IMAGE SEARCH")
                logger.info("="*80)
                try:
                    finder = GoogleImageSearchFinder(download_dir=input_folder)
                    logger.info(f"\nSearching for: {search_keyword}")
                    results = finder.search_by_keyword(search_keyword, num_results=num_results)
                    # Persist metadata
                    output_file = _Path(self.metadata_path)
                    with open(output_file, 'w') as f:
                        json.dump(results, f, indent=2)
                    # Download images and update metadata with download stats
                    download_stats = finder.download_images(results)
                    results['download_stats'] = download_stats
                    with open(output_file, 'w') as f:
                        json.dump(results, f, indent=2)
                    if download_stats.get('downloaded_count', 0) == 0:
                        logger.error("\nERROR No images downloaded from Google search.")
                        return []
                    logger.info(f"\nOK Downloaded {download_stats['downloaded_count']} images")
                except Exception as e:
                    logger.error(f"\nERROR Error during Google Image Search: {e}")
                    traceback.print_exc()
                    return []

            # Step 2: Perform similarity search
            results = self.perform_similarity_search(input_folder)
            
            if not results:
                logger.warning("\nNo results generated")
                return []
            
            # Extract source page URLs
            source_urls = []
            for result in results:
                if "source_page" in result and result["source_page"]:
                    if result["similarity_score"] >= 55.0:  # Threshold for considering a match
                        source_urls.append(result["source_page"])
            
            # Step 3: Cleanup (optional)
            if cleanup:
                logger.info("\n" + "="*80)
                logger.info("CLEANING UP TEMPORARY FILES")
                logger.info("="*80)
                self.cleanup_temp_files()
            
            # Final summary
            logger.info("\n" + "="*80)
            logger.info("WORKFLOW COMPLETED SUCCESSFULLY!")
            logger.info("="*80)
            logger.info(f"Total results: {len(results)}")
            logger.info(f"Source URLs found: {len(source_urls)}")
            logger.info(f"Results saved to: {Path(self.output_folder).absolute()}")
            
            if source_urls:
                logger.info("\nSource Page URLs:")
                for i, url in enumerate(source_urls, 1):
                    logger.info(f"  {i}. {url}")
            
            return source_urls
            
        except Exception as e:
            logger.error(f"\nERROR Workflow failed: {e}")
            traceback.print_exc()
            
            # Cleanup on error
            if cleanup:
                self.cleanup_temp_files()
            
            return []


def main():
    """Example usage of the custom workflow."""    
    parser = argparse.ArgumentParser(
        description="Custom Pathway Workflow - Face similarity search with file path input"
    )
    parser.add_argument(
        '--face-paths',
        type=str,
        nargs='+',
        required=True,
        help='List of face image file paths'
    )
    parser.add_argument(
        '--input-folder',
        type=str,
        default='input',
        help='Folder containing query images (default: input)'
    )
    parser.add_argument(
        '--output-folder',
        type=str,
        default='output',
        help='Folder to save results (default: output)'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Keep temporary database files after processing'
    )
    
    args = parser.parse_args()
    
    try:
        # Create workflow
        workflow = CustomPathwayWorkflow(
            face_image_paths=args.face_paths,
            output_folder=args.output_folder
        )
        
        # Run workflow
        source_urls = workflow.run(
            input_folder=args.input_folder,
            cleanup=not args.no_cleanup
        )
        
        # Print results
        if source_urls:
            print("\n" + "="*80)
            print("SOURCE PAGE URLS")
            print("="*80)
            for url in source_urls:
                print(url)
        else:
            print("\nNo source URLs found")
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
