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
        self.extention = "txt"

        self.get_separator()
        ## get local ip
        self.get_local_ip()

        ## прочитать конфиг, считать путь к данным
        #self.datadirname = 'data/Съемка'
        self.datadirname = "D:\\AerosolComplex\\YandexDisk\\ИКМО org.msu\\_Instruments\\_Grimm5416\\_Today"
        self.logdirname  = ".\\log"
        if not self.datadirname.endswith(self.sep): self.datadirname += self.sep
        if not self.logdirname.endswith(self.sep):  self.logdirname  += self.sep
        if not os.path.isdir(self.logdirname):
            os.mkdir(self.logdirname)


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
    ##  определить окончание слова "час" в зависимости от числа 
    ## 1 час, 2 часа, 5 часов, 21 час
    ## ----------------------------------------------------------------
    def get_ending(self, n):
        n = int(n)
        if n % 10 == 1 and n != 11:
            return ''
        elif 2 <= n % 10 <= 4 and n // 10 != 1:
            return 'а'
        else:
            return 'ов'
        

    ## ----------------------------------------------------------------
    ##  найти самый поздний файл
    ## ----------------------------------------------------------------
    def get_latest_file(self, extention):
        ''' 
        Функция ищет самый поздний файл
        Возвращает его имя
        '''
        max_file = f"{self.device_name} Supervisor: Error! No file found with extention {extention}"

        dirname = self.datadirname
        if not dirname.endswith(self.sep):  dirname = dirname + self.sep
        if not os.path.isdir(dirname):
            #self.print_info(f"{self.device_name} Supervisor: Alarm!! Нет такой папки {dirname}! Валим отсюда!")
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
    ##  прочитать и проверить содержимое файла
    ## ----------------------------------------------------------------
    def check_file_data(self):
        ## прочитать файл
        try:
            #data = pd.read_csv(last_file, sep="\t") ## Error 'utf-8' codec can't decode byte 0xb0 in position 1573: invalid start byte
            #data = pd.read_csv(last_file, sep="\t", encoding = "ISO-8859-1") ## тоже работает
            data = pd.read_csv(self.last_file, sep="\t", encoding = "latin")
        except Exception as error:
            self.print_info(f"{self.device_name} Supervisor: Error in file reading: {error}")
            return 2
        #print(data.tail(20))

        ## если в файле нет данных - ошибка в телебот
        if data.shape[0] == 0:
            self.print_info(f"{self.device_name} Supervisor: No data in file {self.last_file}")
            return 3

        ## если одна колонка - 
        if data.shape[1] == 1:
            self.print_info(f"{self.device_name} Supervisor: No columns in file {self.last_file}")
            return 4
        
        self.data = data ## \todo оставить две недели
        return 0


    ## ----------------------------------------------------------------
    ##  найти и проверить самый поздний файл
    ## ----------------------------------------------------------------
    def check_lastfile(self):
        last_file = self.get_latest_file(self.extention)
        self.last_file = last_file
        #self.print_message(self.last_file)

        ## если файла нет - ошибка в телебота
        if "error" in last_file.lower():
            self.print_info(last_file)
            return 1

        ## если файл не менялся 2 часа - ошибка в телебот
        now = time.time() ## текущее время
        delta = int(now - os.path.getmtime(last_file)) // 60 ## minutes
        if delta > self.alarm_time: # 60 min
            text  = f"{self.device_name.upper()} Supervisor: Файл \"{last_file}\" не менялся "
            text += f"{delta // 60} час{self.get_ending(delta // 60)}" 
            text += f" ({delta} минут)" * (delta < 60)
            ## послать предупреждение, что самый поздний файл очень старый
            self.print_info(text)
            #self.print_message(text)

        #self.check_file_data()
        return 0


############################################################################
############################################################################
if __name__ == "__main__":
    guard = Supervisor("TCA08")
    guard.datadirname = "D:\\AK\\TCA08\\data\\OnlineResult"
    guard.extention = "csv"
    try:
        if guard.check_lastfile():
            #exit("Errors with last file") 
            pass            
    except Exception as error:
        guard.write_to_bot(f"{guard.device_name} Supervisor: {error}")
        
        
    guard = Supervisor("AE33")
    guard.datadirname = "D:\\AK\\AE33-S09\\data\\table"
    guard.extention = "csv"
    try:
        if guard.check_lastfile():
            #exit("Errors with last file")
            pass
    except Exception as error:
        guard.write_to_bot(f"{guard.device_name} Supervisor: {error}")