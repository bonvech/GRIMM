import os, time
from datetime import datetime
import pandas as pd
import socket
import telebot
import telebot_config

import numpy as np
import matplotlib.pyplot as plt
from   matplotlib import dates

from   supervisor import *


############################################################################
############################################################################
class Grimm(Supervisor):
    def __init__(self):
        super().__init__("grimm")
        path_to_figures = ".\\figures\\"
        self.alarm_time = 60


    ## ----------------------------------------------------------------
    ##  проверить время самой последней записи в файле
    ## ----------------------------------------------------------------
    def check_last_record(self): 
        ##  прочитать и проверить данные в файле
        self.check_file_data()
        
        ## сравнить время последнего измерения с текущим 
        if "Time End" not in self.data.columns:
            self.print_info("Ошибка при чтении формата данных")
            return 5

        ## прочитать время последней записи (последнего измерения)
        grimm_data_format = '%d/%m/%Y %H:%M:%S'
        last_record = self.data.iloc[-1]
        last_date = time.mktime(time.strptime(last_record["Time End"], grimm_data_format))
        #print(last_record)

        now = time.time() ## текущее время
        delta = int(now - last_date) // 60 ## sec -> minuts
        #print(last_record["Time End"], now, last_date)
        #print(delta)

        ## если время больше чем час - сообщение
        if delta > self.alarm_time: # 60 min
            text  = f"{self.device_name.upper()}: Нет новых данных. Последняя запись в файле"
            text += f" {delta // 60} час{self.get_ending(delta // 60)} "
            text += f"({delta} минут) " * (delta < 60) 
            text += "назад."
            self.print_info(text)
            return 1
        return 0


    ## ----------------------------------------------------------------
    ##  прочитать ошибки и предупреждения
    ## ----------------------------------------------------------------
    def read_errors_and_wars(self):
        ## расшифрока файла - читать последние 10 записей (1 раз в 4 минут) 
        ## и анализировать ошибки и предупреждения
        n = min(10, self.data.shape[0])
        last_records = self.data.iloc[-n:]

        ##  читать предупреждения
        #print(set(last_records["Warning"]))
        wars = self.get_warnings(last_records["Warning"])
        if wars:
            self.print_info(f"{self.device_name.upper()}: {wars}")

        ##  читать ошибки
        wars = self.get_errors(last_records["Error"])
        if wars:
            self.print_info(f"{self.device_name.upper()}: {wars}")

        return 0


    ## ----------------------------------------------------------------
    ##  собрать варнинги
    ## ----------------------------------------------------------------
    def get_warnings(self, wars):
        warning = 0
        for war in wars:
            warning |= war
    
        message = ""
        if warning & 1:
                message += "Warning 1. Very high concentration (expected error > 5%).\n"
        if warning & 2:
                message += "Warning 2. NO Warmup.\n"
        if warning & 4:
                message += "Warning 4. NO 1-Butanol.\n"
        if warning & 8:
                message += "Warning 8. Low pressure.\n"
        if warning & 16:
                message += "Warning 16. DC < 1mV.\n"
        if warning & 32:
                message += "Warning 32. DC > 1V.\n"
        if warning & 64:
                message += "Warning 64. Counts without flow.\n"
        if warning & 128:
                message += "Warning 128. Counts without laser.\n"
        if warning & 256:
                message += "Warning 256. (C1/C0)<0.99.\n"
        if warning & 512:
                message += "Warning 512. Condensate bottle full.\n"
        if warning & 1024:
                message += "Warning 1024. External 1-Butanol reservoir empty.\n"

        return message


    ## ----------------------------------------------------------------
    ##  собрать ошибки
    ## ----------------------------------------------------------------
    def get_errors(self, wars):
        warning = 0
        try:
            for war in wars:
                warning |= war
        except:
            message = "Errors!! Unknown format of error!"
            return message
        
        message = ""
        if warning & 1:
            message += "Error 1. Condensate Outlet or Liquid Inlet. (Connect the respective bottle).\n"
        if warning & 2:
            message += "Error 2. Fan Error (To be checked by a service technician).\n"
        if warning & 4:
            message += "Error 4. 1-Wire-not OK (To be checked by a service technician).\n"
        if warning & 8:
            message += "Error 8. Liquidlevel not OK (Fill up external 1-Butanol reservoir).\n"
        if warning & 16:
            message += "Error 16. Flow or Aerosolinlet or Underpressure or Pump not OK: "
            message += "(Remove Saturator key from the aerosol inlet) or (Open bottle cap (LED green?)) or (Remove all protective caps).\n"
        if warning & 32:
            message += "Error 32. Temperature! (Terminate warm-up).\n"
        if warning & 64:
            message += "Error 64. Memo not OK (USB stick not recognized or USB stick capacity full).\n"
        if warning & 128:
            message += "Error 128. Fatal Error: Laser not OK (To be checked by a service technician).\n"     
        if warning & 512:
            message += "Error 512. Low Pressure Check sample probe, Sample flow blocked Low ambient pressure).\n"
        if warning & 1024:
            message += "Error 1024. Sheath Air Flow (Remove all protective caps).\n"

        return message


## ----------------------------------------------------------------
##  Return datatime format
## ----------------------------------------------------------------
def get_time_format():
    ##  check if format is possible
    fmt = dates.DateFormatter('%d-%2m-%Y\n %H:%M')
    try:
        print(datetime.now().strftime(fmt))
    except:
        fmt = dates.DateFormatter('%d/%m/%Y\n %H:%M')
    return fmt


## ----------------------------------------------------------------
##  Plot
## ----------------------------------------------------------------
def plot_figure(data, period='day'):
    path_to_figures = ".\\figures\\"
    filetype = "day"
    title = 'GRIMM'

    xparam, yparam = 'Time End', 'Total [1/ccm]'
    #data['Time End'], data['Total [1/ccm]']
    grimm_data_format = '%d/%m/%Y %H:%M:%S'

    x = pd.to_datetime(data[xparam].astype('string'), format=grimm_data_format)
    if period == 'day':
        xmin = x.max() - pd.to_timedelta("48:00:00")
    else:
        xmin = x.max() - pd.to_timedelta("336:00:00")
    data = data[pd.to_datetime(data[xparam], format=grimm_data_format) > xmin]
    x = x[x > xmin]
    xlims = (x.min(), x.max() + pd.to_timedelta("2:00:00"))
    print('xmin:', xmin)

    ## format graph
    plt.rcParams['xtick.labelsize'] = 10
    facecolor = 'white'
    p1color = "hotpink" #'orchid'  #'green'
    #p2color = 'dimgray'

    fig = plt.figure(figsize=(10, 5))
    ax_2 = fig.add_subplot(1, 1, 1)
    
    ##  plot first param
    param1 = yparam
    y = data[param1].replace(0, np.nan)
    #print(y, data[param1])
    ax_2.plot(x, y, p1color, label=param1, linewidth=4)
    #ax_2.fill_between(x, y, np.zeros_like(y), color=p1color)
   
    ##  format graph
    ax_2.set_xlim(xlims)
    ax_2.set_ylim(bottom=0)
    ax_2.set_title(title, loc='right')
    ax_2.legend()

    fmt = get_time_format()
    locator = dates.AutoDateLocator(minticks=20, maxticks=30)

    ax_2.xaxis.set_major_formatter(fmt)
    ax_2.xaxis.set_minor_locator(locator)
    ax_2.grid(which='major', alpha=0.9)
    ax_2.grid(which='minor', alpha=0.5, linestyle='--')

    plt.savefig(path_to_figures + 'grimm_' + filetype.lower() + '.svg', facecolor='white', bbox_inches='tight') 
    plt.savefig(path_to_figures + 'grimm_' + filetype.lower() + '.png', facecolor='white', bbox_inches='tight') 



############################################################################
############################################################################
if __name__ == "__main__":
    try:
        grimm = Grimm()
        if grimm.check_lastfile():
            exit("Errors with last file")
        if grimm.check_last_record():
            exit("Errors in file format or in last record")
        grimm.read_errors_and_wars()
        plot_figure(grimm.data, period='day')
    except Exception as error:
        grimm.write_to_bot(f"{error}")