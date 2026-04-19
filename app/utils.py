def get_age_group(age: int | None) -> str:
    if age is None:
        return "unknown"
    
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"
