
import re

def parse_views_id(views_str: str) -> int:
    """
    Parses Indonesian YouTube view counts to integer.
    Examples:
    - "1,2 jt x ditonton" -> 1200000
    - "123 rb x ditonton" -> 123000
    - "500 x ditonton" -> 500
    - "1.234 x ditonton" -> 1234
    """
    if not views_str:
        return 0
    
    # Normalize: lowercase, remove "x ditonton", "views", etc. keep numbers, commas, dots, letters
    clean_str = views_str.lower().replace("x ditonton", "").replace("views", "").strip()
    
    # Check for multiplier
    multiplier = 1
    if "jt" in clean_str:
        multiplier = 1_000_000
        clean_str = clean_str.replace("jt", "").strip()
    elif "rb" in clean_str:
        multiplier = 1_000
        clean_str = clean_str.replace("rb", "").strip()
    elif "m" in clean_str: # Millions in english just in case
        multiplier = 1_000_000
        clean_str = clean_str.replace("m", "").strip()
    elif "k" in clean_str: # Thousands in english just in case
        multiplier = 1_000
        clean_str = clean_str.replace("k", "").strip()
        
    # Handle Java/Indonesian number formatting
    # "1,2" (decimal comma) -> 1.2
    # "1.234" (thousand separator dot) -> 1234
    
    # If it contains both dot and comma, assume standard Indonesian: 1.234,56 (unlikely for views, usually 1,2 jt)
    # Most common patterns:
    # 1,2 -> 1.2
    # 1.200 -> 1200
    
    try:
        if "," in clean_str:
            clean_str = clean_str.replace(".", "") # Remove thousand separators if any mixed (rare)
            clean_str = clean_str.replace(",", ".") # Convert decimal comma to dot
            num = float(clean_str)
        else:
            # removing dots as thousands separator
            clean_str = clean_str.replace(".", "")
            num = float(clean_str)
            
        return int(num * multiplier)
    except ValueError:
        return 0
