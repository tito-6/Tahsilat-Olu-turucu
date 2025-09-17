"""
Turkish character utilities for proper case conversion
Handles I, i, İ, ı characters correctly
"""

def turkish_upper(text):
    """Convert text to uppercase with proper Turkish character handling"""
    if not text:
        return text
    
    result = str(text)
    
    # Handle Turkish-specific characters first
    turkish_mappings = {
        'i': 'İ',
        'ı': 'I',
        'ğ': 'Ğ',
        'ü': 'Ü',
        'ş': 'Ş',
        'ö': 'Ö',
        'ç': 'Ç'
    }
    
    # Apply Turkish character mappings
    for lower_char, upper_char in turkish_mappings.items():
        result = result.replace(lower_char, upper_char)
    
    # Apply standard upper() for remaining characters
    result = result.upper()
    
    return result

def turkish_lower(text):
    """Convert text to lowercase with proper Turkish character handling"""
    if not text:
        return text
    
    result = str(text)
    
    # Handle Turkish-specific characters first
    turkish_mappings = {
        'İ': 'i',
        'I': 'ı',
        'Ğ': 'ğ',
        'Ü': 'ü',
        'Ş': 'ş',
        'Ö': 'ö',
        'Ç': 'ç'
    }
    
    # Apply Turkish character mappings
    for upper_char, lower_char in turkish_mappings.items():
        result = result.replace(upper_char, lower_char)
    
    # Apply standard lower() for remaining characters
    result = result.lower()
    
    return result

def turkish_contains(text, substring):
    """Check if text contains substring with proper Turkish case handling"""
    if not text or not substring:
        return False
    
    return turkish_lower(substring) in turkish_lower(text)

def turkish_starts_with(text, prefix):
    """Check if text starts with prefix with proper Turkish case handling"""
    if not text or not prefix:
        return False
    
    return turkish_lower(text).startswith(turkish_lower(prefix))

def turkish_equals(text1, text2):
    """Check if two texts are equal with proper Turkish case handling"""
    if not text1 and not text2:
        return True
    if not text1 or not text2:
        return False
    
    return turkish_lower(text1) == turkish_lower(text2)
