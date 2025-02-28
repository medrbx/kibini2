import datetime
import numpy as np

"""
Obtenir à partir d'un horodotage un arrêt du Zèbre
"""

def time_in_range(start, end, x):
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end

def get_zebre_stop_by_datetime(dt):
    stop = 'INC'
    if isinstance(dt, datetime.date):
        # Mardi
        if dt.strftime('%w') == '2':
            # 14h30 - 16h
            start = datetime.time(14, 20, 0)
            end   = datetime.time(16, 15, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B01'
            # 16h30 - 18h
            start = datetime.time(16, 16, 0)
            end   = datetime.time(18, 10, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B03'

        # Mercredi
        if dt.strftime('%w') == '3':
            # 9h30 - 10h30
            start = datetime.time(9, 20, 0)
            end   = datetime.time(10, 45, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B24'
            # 11h00 - 12h
            start = datetime.time(10, 46, 0)
            end   = datetime.time(12, 15, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B23'
            # 14h -15h
            start = datetime.time(13, 55, 0)
            end   = datetime.time(15, 14, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B07'
            # 15h30 - 16h30
            start = datetime.time(15, 15, 0)
            end   = datetime.time(16, 37, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B08'
            # 16h45 - 17h45
            start = datetime.time(16, 38, 0)
            end   = datetime.time(18, 0, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B09'

        # Jeudi
        if dt.strftime('%w') == '4':
            # 15h - 16h
            start = datetime.time(14, 50, 0)
            end   = datetime.time(16, 10, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B13'
            # 16h15 - 17h30
            start = datetime.time(16, 11, 0)
            end   = datetime.time(17, 45, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B25'

        # Vendredi
        if dt.strftime('%w') == '5':
            # 15h - 16h
            start = datetime.time(14, 50, 0)
            end   = datetime.time(16, 10, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B22'
            # 16h15 - 17h30
            start = datetime.time(16, 11, 0)
            end   = datetime.time(17, 45, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B14'

        # Samedi
        if dt.strftime('%w') == '6':
            # 9h30 - 10h30
            start = datetime.time(9, 20, 0)
            end   = datetime.time(10, 40, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B20'
            # 11h00 - 12h00
            start = datetime.time(10, 50, 0)
            end   = datetime.time(12, 8, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B17'
            # 14h - 15h
            start = datetime.time(13, 50, 0)
            end   = datetime.time(15, 10, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B21'
            # 15h15 - 16h30
            start = datetime.time(15, 11, 0)
            end   = datetime.time(16, 45, 0)
            if time_in_range(start, end, dt.time()):
                stop = 'B19'
    return stop
