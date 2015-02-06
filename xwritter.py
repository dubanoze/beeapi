from openpyxl import Workbook
from os.path import curdir

def ex_write(values, names=['col1','col2','col3'],
             path='result.xlsx', wsname='Sheet1'):
    wb = Workbook(write_only=True)
    ws = wb.create_sheet()
    ws.title = wsname
    ws.append(names)
    for row in range(len(values)):
        ws.append(values[row])

    wb.save(path)