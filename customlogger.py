#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 25 16:30:53 2019

@author: andreamontes
"""
class CustomLogger(object):
     def __init__(self, logger, level):
          #Needs a logger and a logger level
          self.logger = logger
          self.level = level
     
     def changeLogger(self, logger):
          self.logger = logger
          
     def write(self, message):
          #Only log if there is a message (not just a new line)
          if message.rstrip() != "":
               self.logger.log(self.level, message.rstrip())
