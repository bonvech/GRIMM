import os, time
from datetime import datetime
import pandas as pd
import socket
import telebot
import telebot_config

import numpy as np
import matplotlib.pyplot as plt
from   matplotlib import dates


class Supervisor:
    def __init__(self, devicename):
        self.bot_flag = True ## 
        self.test_mode = False
        self.telebot_config_token   = telebot_config.token
        self.telebot_config_channel = telebot_config.channel
        self.device_name = devicename
        self.alarm_time  = 60 # 60 min

        self.get_separator()
        ## get local ip
        self.get_local_ip()

        ## прочитать конфиг, считать путь к данным
        #self.datadirname = 'data/Съемка'
        self.datadirname = "D:\\AerosolComplex\\YandexDisk\\ИКМО org.msu\\_Instruments\\_Grimm5416\\_Today"
        self.logdirname  = ".\\log"
        if not self.datadirname.endswith(self.sep): self.datadirname += self.sep
        if not self.logdirname.endswith(self.sep):  self.logdirname  += self.sep


    ## ----------------------------------------------------------------
    ##  
    ## ----------------------------------------------------------------
    def get_local_ip(self):
        self.hostname = socket.gethostname()
        self.local_ip = socket.gethostbyname(self.hostname)
        #return hostname, local_ip


    ## ----------------------------------------------------------------
    ##  Print message to bot or to logfile
    ## ----------------------------------------------------------------
    def print_info(self, text):
        if self.bot_flag:
            self.write_to_bot(text)
        else:
            self.print_message(text)


    ## ----------------------------------------------------------------
    ##  Print message to logfile
    ## ----------------------------------------------------------------
    def print_message(self, message, end=''):
        ## print to screen
        print(message)

        ## write to logfile
        if message[-1] != '\n' and end != '\n':
            message += '\n'
        #sep = self.get_separator()
        #if not logdirname.endswith(sep):  logdirname += sep
        logfilename = self.logdirname + "_".join(["_".join(str(datetime.now()).split('-')[:2]), 
                                                 self.device_name,  'log.txt'])
        with open(logfilename,'a') as flog:
            flog.write(f"{datetime.now()}:  {message}{end}")


    ## ----------------------------------------------------------------
    ##  write message to bot
    ## ----------------------------------------------------------------
    def write_to_bot(self, text):
        text = f"{self.hostname} ({self.local_ip}): {text}"
        if not self.test_mode:
            try:
                bot = telebot.TeleBot(self.telebot_config_token, parse_mode=None)
                bot.send_message(self.telebot_config_channel, text)
                self.print_message(text)
            except Exception as err:
                ##  напечатать строку ошибки
                text = f": ERROR in writing to bot: {err}"
                self.print_message(text)  ## write to log file
        else:
            self.print_message(text)        


    ## ----------------------------------------------------------------
    ##  определить разделитель в полном пути в операционной системе 
    ## ----------------------------------------------------------------
    def get_separator(self):
        self.sep = '/' if 'ix' in os.name else '\\' 


    ## ----------------------------------------------------------------
    ##  найти самый поздний файл
    ## ----------------------------------------------------------------
    def get_latest_file(self, extention):
        ''' 
        Функция ищет самый поздний файл
        Возвращает его имя
        '''
        max_file = f"Error! No file found with extention {extention}"

        dirname = self.datadirname
        if not dirname.endswith(self.sep):  dirname = dirname + self.sep
        if not os.path.isdir(dirname):
            #self.print_info(f"Alarm!! Нет такой папки {dirname}! Валим отсюда!")
            return f"Error! Нет такой папки {dirname}!" 

        max_atime = 0
        #print(os.listdir(dirname))
        for filename in os.listdir(dirname):
            ## проверить файл ли это
            if not os.path.isfile(dirname + filename):
                continue
            if not filename.endswith(extention):
                continue
            if os.path.getmtime(dirname + filename) > max_atime:
                max_atime = os.path.getmtime(dirname + filename)
                max_file = dirname + filename
        return max_file


    ## ----------------------------------------------------------------
    ##  найти и проверить самый поздний файл
    ## ----------------------------------------------------------------
    def check_file_data(self):
        ## прочитать файл
        try:
            #data = pd.read_csv(last_file, sep="\t") ## Error 'utf-8' codec can't decode byte 0xb0 in position 1573: invalid start byte
            #data = pd.read_csv(last_file, sep="\t", encoding = "ISO-8859-1") ## тоже работает
            data = pd.read_csv(self.last_file, sep="\t", encoding = "latin")
        except Exception as error:
            self.print_info(f"Error in file reading: {error}")
            return 2
        #print(data.tail(20))

        ## если в файле нет данных - ошибка в телебот
        if data.shape[0] == 0:
            self.print_info(f"No data in file {last_file}")
            return 3

        ## если одна колонка - 
        if data.shape[1] == 1:
            self.print_info(f"No columns in file {last_file}")
            return 4
        
        self.data = data ## \todo оставить две недели
        return 0


    ## ----------------------------------------------------------------
    ##  найти и проверить самый поздний файл
    ## ----------------------------------------------------------------
    def check_lastfile(self):
        last_file = self.get_latest_file("txt")
        self.last_file = last_file
        #self.print_message(self.last_file)

        ## если файла нет - ошибка в телебота
        if "error" in last_file.lower():
            self.print_info(last_file)
            return 1

        ## если файл не менялся 2 часа - ошибка в телебот
        now = time.time() ## текущее время
        delta = (now - os.path.getmtime(last_file)) // 60 ## minutes
        if delta > self.alarm_time: # 60 min
            text = f"Файл \"{last_file}\" не менялся {delta / 60:.0f} часов ({delta:.0f} минут)"
            ## послать предупреждение, что самый поздний файл очень старый
            self.print_info(text)
            #self.print_message(text)

        self.check_file_data()
        return 0


############################################################################
############################################################################
class Grimm(Supervisor):
    def __init__(self):
        super().__init__("grimm")
        path_to_figures = ".\\figures\\"


    ## ----------------------------------------------------------------
    ##  проверить время самой последней записи в файле
    ## ----------------------------------------------------------------
    def check_last_record(self):        
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
        delta = (now - last_date) // 60 ## sec
        #print(last_record["Time End"], now, last_date)
        #print(delta)

        ## если время больше чем час - сообщение
        if delta > 60: # 60 min
            self.print_info(f"{self.device_name.upper()}: Нет новых данных. Последняя запись в файле {delta / 60:.0f} часов ({delta:.0f} минут) назад")
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