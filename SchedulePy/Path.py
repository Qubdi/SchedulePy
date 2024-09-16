import os
import pathlib

def make_directory(save_path):
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    return save_path

def current_path_and_path_list():
    # This is the full path of the file from which this function will be run
    whole_path = pathlib.Path().resolve()

    # it returns same values but written in list
    path_list = str(whole_path).split("\\")

    return whole_path, path_list