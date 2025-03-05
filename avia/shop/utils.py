def format_amount(value):
    try:
        value = float(value)
    except:
        return 0
    
    return '{:,.2f}'.format(value).replace(',', ' ')


def escape_markdown(text: str) -> str:
    characters_to_escape = ['_', '*', '[', ']', '`']
    for char in characters_to_escape:
        text = text.replace(char, '\\' + char)

    return text
