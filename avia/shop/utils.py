def format_amount(value):
    try:
        value = float(value)
    except:
        return 0
    
    return '{:,.2f}'.format(value).replace(',', ' ')
