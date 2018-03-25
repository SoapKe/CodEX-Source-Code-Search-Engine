# coding=utf-8
"""
Created on 23/03/2018
Author: Ciarán
"""

import re
import json
import os
import nltk

from FCI.FormattedCodeInterface import FormattedCodeInterface
from LogWriter import LogWriter
import FCI.FCIConverter


class CreateJsonFiles:

    def __init__(self):
        self.clean_projects_path = None
        self.unclean_projects_path = None
        self.remote_json_path = None

        self.json_data = None
        self.project_info = {}  # Dictionary with project names and containing directory as key and corresponding json data as value

        self.log_writer = LogWriter()

    def load_file_paths(self):
        file_paths_config_file = open("../file_paths.json")
        file_paths = json.load(file_paths_config_file)

        self.clean_projects_path = file_paths["Linux"]["clean_dir"]
        self.unclean_projects_path = file_paths["Linux"]["unclean_dir"]
        self.remote_json_path = file_paths["Linux"]["json_dir"]

    # For each json file from Kirk find the corresponding clean project
    # For each file within that project crete an fci object with the details of that file
    def run(self):
        self.load_file_paths()
        self.find_all_json_files()

        for project_name in self.project_info:
            self.json_data = self.project_info[project_name]
            self.find_all_source_files(self.clean_projects_path + project_name)

    # Goes through each unclean folder and searches for all json files from Kirk
    # When a file is found it saves it to a directory with the folder and file name as a key
    # and the json data as the element
    def find_all_json_files(self):
        for directory in os.listdir(self.unclean_projects_path):
            projects = self.unclean_projects_path + "/" + directory
            if os.path.isdir(projects):
                self.log_writer.write_info_log("Reading jsons from " + directory)
                for file in os.listdir(projects):
                    if file.endswith(".json"):
                        json_path = "/" + directory + "/" + file
                        json_file = open(self.unclean_projects_path + json_path)
                        # Save the json_path without '.json' at the end to get the name of the unzipped project
                        self.project_info[json_path[:-5]] = json.load(json_file)

    # Goes through all files in a cleaned project and creates an fci object for each
    # Initially the path to a project is passed and the function recursively goes through all files in the project
    def find_all_source_files(self, parent_directory):
        try:
            for file_name in os.listdir(parent_directory):
                file_path = parent_directory + '/' + file_name
                if file_name.endswith(".py"):
                    self.save_file_details_to_fci_object(file_path, file_name)
                else:
                    if os.path.isdir(file_path):
                        self.find_all_source_files(file_path)
                    else:  # Just an extra check to make sure no other files are left
                        self.log_writer.write_warning_log(file_path + " not deleted")
        except Exception as e:
            self.log_writer.write_error_log(str(e))

    # Saves the details of an individual file to an fci object
    def save_file_details_to_fci_object(self, file_path, file_name):
        fci_object = FormattedCodeInterface()

        fci_object.set_file_name(file_name)
        fci_object.set_save_path(file_path)
        self.set_content(file_path, fci_object)
        self.set_project_details(fci_object)

        self.save_fci_objects_to_json_files(fci_object)
        self.log_writer.write_info_log(file_path + " documented.")

    # Save the content, code, and comments of an individual file to an fci object
    def set_content(self, file_path, fci_object):
        file = open(file_path)
        content = ''
        comments_list = []
        python_comments = ['\"\"\"((.|\n)*)\"\"\"', '\'\'\'((.|\n)*)\'\'\'', '#.*']

        # Content
        for line in file.readlines():
            content += line
        fci_object.set_content(content)

        # Code
        code = content
        for comment_pattern in python_comments:
            comments_list += re.findall(comment_pattern, code)
            code = re.sub(comment_pattern, '', code)
        fci_object.set_code(code)

        # Comments
        comments = self.format_comments(comments_list)
        fci_object.set_comments(comments)

    def format_comments(self, comments_list):
        filtered_comments_list = []
        stopwords = set(nltk.corpus.stopwords.words('english'))

        for comment in comments_list:
            for word in comment.split(' '):
                if word.startswith('#'):
                    word = word[1:]

                if word.endswith('.') or word.endswith(','):
                    word = word[:-1]

                if (word not in stopwords) and (word is not '#') and (word is not ''):
                    filtered_comments_list.append(word)

        comments = ' '.join(filtered_comments_list)
        return comments.lower()

    # Saves the details of the current project to an fci object
    def set_project_details(self, fci_object):
        fci_object.set_author(self.json_data["owner_name"])
        fci_object.set_description(self.json_data["description"])
        fci_object.set_language(self.json_data["language"])
        fci_object.set_project_name(self.json_data["name"])
        # fci.set_quality(data["items"][0]["owner"])
        # fci.set_save_time()
        fci_object.set_update_at(self.json_data["updated_at"])
        fci_object.set_url(self.json_data["html_url"])
        fci_object.set_wiki(self.json_data["has_wiki"])

    # Converts fci objects to json files and saves them remotely
    def save_fci_objects_to_json_files(self, fci_object):
        FCI.FCIConverter.to_local_json_file(self.remote_json_path, fci_object)
        self.log_writer.write_info_log("Json files saved to remote machine at " + self.remote_json_path)
