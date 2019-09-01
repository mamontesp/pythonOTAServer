#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading

class CustomThread(threading.Thread):
     def __init__(self, target, connection, address):
          threading.Thread.__init__(self, target=target, args=(connection, address))
