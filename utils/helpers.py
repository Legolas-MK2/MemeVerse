def format_number(value):
    """
    Format a number for display (e.g., 1000 -> 1K, 1000000 -> 1M)
    """
    if value is None:
        return "0"
    if value >= 1000000:
        return f'{value/1000000:.1f}M'
    elif value >= 1000:
        return f'{value/1000:.1f}K'
    return str(value)
