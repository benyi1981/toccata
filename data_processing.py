def get_financial_quarter(month):
    if month <= 3:
        return 'Q3'
    elif month <= 6:
        return 'Q4'
    elif month <= 9:
        return 'Q1'
    elif month <= 12:
        return 'Q2'
    else:
        return 'Invalid Month'

    
def get_financial_year(date):
    if date.month >= 7:
        return date.year  # July to December of the same year
    else:
        return date.year - 1  # January to June of the previous year

def get_financial_year_quarter(financial_year_qtr):
    financial_year, financial_qtr = financial_year_qtr['join_fin_yr'], financial_year_qtr['join_quarter']
    return f"FY{financial_year}{financial_qtr}"