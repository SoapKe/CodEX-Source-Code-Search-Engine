# coding=utf-8
"""
Created on 25/03/2018
Author: Ciarán
"""


class CreateJsonFilesInterface:

    def __init__(self, connection):
        self.connection = connection

    def run(self):
        path_to_file = "/home/ubuntu/Final-Year-Project/Ciaran's Workspace/FCI/CreateJsonFiles.py"
        command = "pyhton3.5 " + path_to_file
        self.connection.exec_command(command)
