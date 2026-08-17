import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Get initials from a name (e.g., "Jack Sparrow" -> "JS", "All Might" -> "AM")
 */
export function getInitials(name: string): string {
  if (!name) return "U";
  
  const words = name.trim().split(/\s+/);
  
  if (words.length === 1) {
    // Single word: take first two characters
    return words[0].substring(0, 2).toUpperCase();
  }
  
  // Multiple words: take first letter of each word, up to 2 letters
  return words
    .slice(0, 2)
    .map(word => word.charAt(0))
    .join("")
    .toUpperCase();
}

/**
 * Format RPS score for display
 * RPS scores are stored in the database as 0-1 (decimal format)
 * This function displays the score in 0-1 format (not percentage)
 * 
 * @param score - RPS score in 0-1 format (from API)
 * @param decimals - Number of decimal places (default: 4)
 * @returns Formatted string in 0-1 format (e.g., "0.4250")
 */
export function formatRpsScore(score: number | null | undefined, decimals: number = 4): string {
  if (score === null || score === undefined) return 'N/A';
  return score.toFixed(decimals);
}

/**
 * Format RPS score as a number (kept in 0-1 format)
 * Useful for calculations or when you need the numeric value
 * 
 * @param score - RPS score in 0-1 format (from API)
 * @param decimals - Number of decimal places (default: 4)
 * @returns Number value (0-1 range)
 */
export function formatRpsScoreAsNumber(score: number | null | undefined, decimals: number = 4): number {
  if (score === null || score === undefined) return 0;
  return parseFloat(score.toFixed(decimals));
}
