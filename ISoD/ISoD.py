# -*- coding: UTF-8 -*-

__author__ = "Alexander M. Puetz"
__date__ = "$2017-11-09$"


import glob
import sys
import os
import numpy as np
import pandas as pd
import peakutils as pku
import re
import shutil

def read_raw_file(filename):
    """
    Read raw file into DataFrame --- c.f. Rudolphi's solution
    """
    return null

def tidy_up():
    """
    Delete previous output folders and recreate them
    """
    print("Cleaning up...")
    try:
        shutil.rmtree("./no_peaks_found/")
        shutil.rmtree("./peaks_found/")
    except:
        pass
    try: os.makedirs("./no_peaks_found/")
    except:
        try: os.makedirs("./no_peaks_found/")
        except: raise PermissionError("Please try again")
    try: os.makedirs("./peaks_found/")
    except:
        try: os.makedirs("./peaks_found/")
        except: raise PermissionError("Please try again")

def write_config(parameters):
    """
    Write out the detection parameters to the config file "./Config.txt"
    """
    with open("Config.txt","w") as config: config.write(f"peak_threshold = {parameters[0]} # Normalized peak detection limit ([0,1], default = 0.1)\nover_mean = {parameters[1]} # Minimum relative peak intensity over mean (both range and full diffractogram, [0:], default = 1.2)\nmin_distance = {parameters[2]} # Minimum peak distance in degrees ([0.1,5], default = 1.0)\nbackground = {parameters[3]} # Minimum counts ([0:], default = 200)")
    # remember: "w" mode will replace the current file

def get_input():
    """
    Ask the user for minimum and maximum 2theta values and allow them to change thresholds
    """
    global min_2theta, max_2theta, peak_threshold, over_mean, min_distance, background, path, directory
    yes = ["y","Y","yes","Yes","j","J","ja","Ja","1"]
    other_directory = str(input("\nEnter path to XRD data if desired (default = ./xrd_data/): "))
    if other_directory == "":
        directory = f".{os.sep}xrd_data{os.sep}"
    else:
        if other_directory.endswith("/") or other_directory.endswith("\\"): pass
        else: other_directory += os.sep # on macOS this doesn't seem to work, since omiting the '/' raises the ValueError
        if os.path.isdir(other_directory): directory = other_directory
        else: raise ValueError("Entered path does not exist.")
        directory = os.path.normpath(directory) + os.sep
    print(f"\n  --> Path set to {directory}")
    print("\nPlease specify your desired 2theta range:") # get minimum and maximum 2theta values
    try:
        min_2theta = float(input("\n  Minimum = "))
        max_2theta = float(input("  Maximum = "))
        # min_2theta = 7.5
        # max_2theta = 8.5
    except:
        raise ValueError("Invalid value entered")
    if min_2theta >= max_2theta: raise ValueError("Invalid range entered")

    use_config = input("\nUse/create config file (y/n)? ")
    if use_config in yes:
        if os.path.isfile("./Config.txt"):
            print("\nConfig file found. Reading in parameters...\n")
            read_config()
        else:
            standard_values = input("\nNo config file found. Create one using standard values (y/n)? ")
            if standard_values in yes:
                write_config([0.1,1.2,1.0,200])
                peak_threshold = 0.1
                over_mean = 1.2
                min_distance = 1.0
                background = 200
            else:
                print("\nPlease enter desired parameters to be saved to config file:")
                parameter_dialog()
                write_config([peak_threshold, over_mean, min_distance, background])
            print("\n  --> Config file created!")

    else:
        change_threshold = input("\nAdjust peak detection parameters (y/n)? ")
        if change_threshold in yes:
            parameter_dialog()
            save_config = input("\nSave new parameters to config file (y/n)? ")
            if save_config in yes: 
                write_config([peak_threshold, over_mean, min_distance, background])
                print("\n  --> Config file changed!")
        peak_threshold = 0.1
        over_mean = 1.2
        min_distance = 1.0
        background = 200

def parameter_dialog():
    """
    Open dialog for the user to enter detection parameters
    """
    global peak_threshold, over_mean, min_distance, background
    try:
        peak_threshold = float(input("\n  Normalized peak detection limit ([0,1], default = 0.1) = "))
        if peak_threshold < 0.01 or peak_threshold > 1: peak_threshold = 0.1
        print(f"  --> Value set to {peak_threshold} (default = 0.1)")
    except:
        print("  --> No or illegal input. Using default value.")
        peak_threshold = 0.1
    try:
        over_mean = float(input("\n  Minimum relative peak intensity over mean ([0:], default = 1.2) = "))
        if over_mean < 0.01: over_mean = 1.2
        print(f"  --> Value set to {over_mean} (default = 1.2)")
    except:
        print("  --> No or illegal input. Using default value.")
        over_mean = 1.2
    try:
        min_distance = float(input("\n  Minimum peak distance in degrees ([0.1,5], default = 1.0) = "))
        if min_distance < 0.1 or min_distance > 5: min_distance = 1.0
        print(f"  --> Value set to {min_distance} (default = 1.0)")
    except:
        print("  --> No or illegal input. Using default value.")
        min_distance = 1.0
    try:
        background = float(input("\n  Minimum counts ([0:], default = 200) = "))
        if background < 0.01: background = 200
        print(f"  --> Value set to {background} (default = 200)")
    except:
        print("  --> No or illegal input. Using default value.")
        background = 200

def read_config():
    """
    Open the config file "./Config.txt" and read in the detection parameters from it
    """
    global peak_threshold, over_mean, min_distance, background
    with open("./Config.txt","r") as config: config_str = config.read()
    try:
        peak_threshold = re.findall('(?<=peak_threshold = )[0-9]*.[0-9]*', config_str)
        peak_threshold = float(peak_threshold[0])
        print(f"  --> Normalized peak detection limit set to {peak_threshold} (default = 0.1).")
    except:
        peak_threshold = 0.1
        print("  --> No value found for peak_threshold, using default.")
    try:
        over_mean = re.findall('(?<=over_mean = )[0-9]*.[0-9]*', config_str)
        over_mean = float(over_mean[0])
        print(f"  --> Minimum relative peak intensity over mean set to {over_mean} (default = 1.2).")
    except:
        over_mean = 1.2
        print("  --> No value found for over_mean, using default.")
    try:
        min_distance = re.findall('(?<=min_distance = )[0-9]*.[0-9]*', config_str)
        min_distance = float(min_distance[0])
        print(f"  --> Minimum peak distance in degrees set to {min_distance} (default = 1.0).")
    except:
        min_distance = 1.0
        print("  --> No value found for min_distance, using default.")
    try:
        background = re.findall('(?<=background = )[0-9]*.[0-9]*', config_str)
        background = float(background[0])
        print(f"  --> Minimum counts set to {background} (default = 200).")
    except:
        background = 200
        print("  --> No value found for background, using default.")

def get_decimal(filename):
    """
    Scan a given CSV-like file for the first occurence of number, dot/comma, number
    """
    try:
        with open(filename, "r") as file:
            data = file.read()
        decimal = re.findall('([0-9](.|,)[0-9])', data) # returns e.g. [("7.9", "."),("1.0", "."), ...]
        return decimal[0][1] # return second value of first tuple, e.g. " "
    # except: raise ValueError(f"Couldn't find delimiter in {filename}")
    except: pass

def get_delimiter(filename):
    """
    Scan a given CSV-like file for delimiters, including comma, semicolon, one or more spaces, and one or more tabs 
    """
    try:
        with open(filename, "r") as file:
            data = file.read()
        delimiter = re.findall('([0-9]%s[0-9]*(,|;|[ ]{1,}|[\t]{1,})[0-9])' % get_decimal(filename), data) # returns e.g. [("7 9", " "),("1 0", " "), ...]
        return delimiter[0][1] # return second value of first tuple, e.g. " "
    # except: raise ValueError(f"Couldn't find delimiter in {filename}")
    except: pass

def combine_ranges():
    """
    Search for samples measured over multiple ranges and combine range data into single XY file
    """
    global skipped
    print("\nCombining multirange scan files...")
    # files = []
    for suffix, rtype in ((suffix, rtype) for suffix in ["xy","xyd"] for rtype in ["_range_","_R"]):
        samples = []
        for filename in glob.iglob(f"{directory}*.{suffix}"):
            if re.search(f"{rtype}\d\d*.{suffix}$", filename): samples.append(re.sub(f"{rtype}\d\d*.{suffix}$", "", filename)) # remove "_range_..." from filename to get samples
        samples = list(set(samples)) # remove duplicate sample names
        for sample in samples:
            if rtype == "_R": df_one = pd.read_csv(f"{sample}{rtype}01.{suffix}", decimal=get_decimal(f"{sample}{rtype}01.{suffix}"), delimiter=get_delimiter(f"{sample}{rtype}01.{suffix}"), skipinitialspace=True, names=["twotheta","counts"], engine="python")
            else: df_one = pd.read_csv(f"{sample}{rtype}1.{suffix}", decimal=get_decimal(f"{sample}{rtype}1.{suffix}"), delimiter=get_delimiter(f"{sample}{rtype}1.{suffix}"), skipinitialspace=True, names=["twotheta","counts"], engine="python")
            try: df_one = df_one.astype(float)
            except: 
                skipped.append(f"{sample}{rtype}n.{suffix}")
                break
            counts = df_one["counts"].values
            for n in range(2,100):
                try:
                    if rtype == "_R": n = str(n).zfill(2)
                    df_temp = pd.read_csv(f"{sample}{rtype}{n}.{suffix}", decimal=get_decimal(f"{sample}{rtype}{n}.{suffix}"), delimiter=get_delimiter(f"{sample}{rtype}{n}.{suffix}"), skipinitialspace=True, names=["twotheta","counts"], engine="python")
                    df_temp = df_temp.astype(float)
                    counts_temp = df_temp["counts"].values
                    counts = [x + y for x, y in zip(counts, counts_temp)]
                except:
                    break
            df_combined = pd.DataFrame.from_items([("twotheta", df_one["twotheta"].values),("counts", counts)])
            df_combined.to_csv(path_or_buf=f"{sample}_ranges_combined.{suffix}", sep=" ", na_rep="", columns=None, header=False, index=False, mode="w")

def extract_range_to_dataframe(filename, min_2theta, max_2theta):
    """
    Extract desired range from XY file into DataFrame
    """
    df_full = pd.read_csv(filename, decimal=get_decimal(filename), delimiter=get_delimiter(filename), skipinitialspace=True, names=["twotheta","counts"], engine="python")
    df_full = df_full.astype(float)
    df_trunc_bottom = df_full[df_full.twotheta > min_2theta]
    df_range = df_trunc_bottom[df_trunc_bottom.twotheta < max_2theta]
    return df_range

def copy_files_to(filename, suffix, new_directory):
    """
    Copy both RAW and XY/XYD file to respective output folder
    """
    combined = ""
    if re.search("_ranges_combined$", filename):
        combined = "_ranges_combined"
        filename = filename.replace("_ranges_combined", "")
    shutil.copy2(f"{filename}{combined}.{suffix}", os.path.join(os.path.normpath(new_directory),f"{os.path.basename(filename)}{combined}.{suffix}"))
    shutil.copy2(f"{filename}.raw", os.path.join(os.path.normpath(new_directory),f"{os.path.basename(filename)}.raw"))

def main():
    # print("""\nooooo  .oooooo..o           oooooooooo.   \n`888' d8P'    `Y8           `888'   `Y8b  \n 888  Y88bo.       .ooooo.   888      888 \n 888   `"Y8888o.  d88' `88b  888      888 \n 888       `"Y88b 888   888  888      888 \n 888  oo     .d8P 888   888  888     d88' \no888o 8""88888P'  `Y8bod8P' o888bood8P'\n\nWelcome to ISoD Sorts Diffractograms!\n(c) Copyright 2017 Alexander M. Pütz\n""")
    # print("""\n_/\/\/\/\____/\/\/\/\/\______________/\/\/\/\/\___\n___/\/\____/\/\____________/\/\/\____/\/\____/\/\_\n___/\/\______/\/\/\/\____/\/\__/\/\__/\/\____/\/\_\n___/\/\____________/\/\__/\/\__/\/\__/\/\____/\/\_\n_/\/\/\/\__/\/\/\/\/\______/\/\/\____/\/\/\/\/\___\n__________________________________________________\n\nWelcome to ISoD Sorts Diffractograms!\n(c) Copyright 2017 Alexander M. Pütz\n""")
    print("""
_____________/\/\/\/\____/\/\/\/\/\______________/\/\/\/\/\__________
______________/\/\____/\/\____________/\/\/\____/\/\____/\/\_________
_____________/\/\______/\/\/\/\____/\/\__/\/\__/\/\____/\/\__________
____________/\/\____________/\/\__/\/\__/\/\__/\/\____/\/\___________
_________/\/\/\/\__/\/\/\/\/\______/\/\/\____/\/\/\/\/\______________
_____________________________________________________________________

                Welcome to ISoD Sorts Diffractograms!
                (c) Copyright 2017 Alexander M. Pütz
    """)
    global skipped
    skipped = []

    tidy_up()
    get_input()
    combine_ranges()

    reflections = []
    with_peak = []
    without_peak = []
    max_filename_length = 0

    print("\nBeginning peak detection...")

    for suffix in ["xy","xyd"]:
        for filename in glob.iglob(f"{directory}*.{suffix}"):
            filename = os.path.normpath(filename)
            filename_without_extension = re.sub(f".{suffix}$", "", filename)
            filename_without_directory = os.path.basename(filename_without_extension)
            if len(f"{filename_without_directory}.{suffix}") > max_filename_length: max_filename_length = len(f"{filename_without_directory}.{suffix}")

        for filename in glob.iglob(f"{directory}*.{suffix}"): # iterate over all {suffix} files in {directory}
            filename = os.path.normpath(filename)
            filename_without_extension = re.sub(f".{suffix}$", "", filename)
            filename_without_directory = os.path.basename(filename_without_extension)
            # if re.search(f"_range_(?:[2-9]|\d\d\d*).{suffix}$", filename): # exclude all but the first range
            if re.search(f"_range_\d\d*.{suffix}$", filename): # exclude all but the combined ranges
                pass # just here because re.search(...) != True doesn't work
            else:
                try: # in case a file contains zero ranges or is faulty
                    df_full = pd.read_csv(filename, decimal=get_decimal(filename), delimiter=get_delimiter(filename), names=["twotheta","counts"], engine='python')
                    df_range = extract_range_to_dataframe(filename,min_2theta,max_2theta)
                    step_size = df_range.iloc[2,0] - df_range.iloc[1,0]
                    peaks = []
                    for index in pku.indexes(df_range["counts"].values, thres=peak_threshold, min_dist=(min_distance/step_size)): # this is index length, get this value from step size
                        if df_range.iloc[index,1] > over_mean * df_full["counts"].mean() and df_range.iloc[index,1] > over_mean * df_range["counts"].mean() and df_range.iloc[index,1] > background: peaks.append("{0:>7.3f}".format(df_range.iloc[index,0]) + "  {0:>8}".format(int(df_range.iloc[index,1])))
                    peaks_str = ("\n" + (max_filename_length + 2) * " ").join(peaks)
                    if peaks_str == "":
                        without_peak.append(f"{filename_without_directory}.{suffix}" + (max_filename_length - len(f"{filename_without_directory}.{suffix}") + 2) * " " + "{0:>7}".format("---") + "  {0:>8}".format("---"))
                        copy_files_to(filename_without_extension, suffix, "./no_peaks_found/")
                    else:
                        with_peak.append(f"{filename_without_directory}.{suffix}" + (max_filename_length - len(f"{filename_without_directory}.{suffix}") + 2) * " " + f"{peaks_str}")
                        copy_files_to(filename_without_extension, suffix, "./peaks_found/")
                except:
                   skipped.append(f"{filename_without_directory}.{suffix}")
                   pass

    with_peak = sorted(with_peak)
    with_peak = "\n".join(with_peak)
    without_peak = sorted(without_peak)
    without_peak = "\n".join(without_peak)
    skipped = sorted(skipped)
    skipped = "\n".join(skipped)
    with open("Results.txt","w") as file: # save results to TXT file
        file.write("Scan File" + (max_filename_length - 6) * " " + "2Theta" + 4 * " " + "Counts\n" + (max_filename_length + 19) * "=" + "\n")
        if with_peak == "": file.write("none\n")
        else: file.write(with_peak + "\n" + (max_filename_length + 19) * "=" + "\n")
        # file.write("\n\n\nNO PEAK FOUND:\n\nScanfile\n" + max_filename_length * "=" + "\n")
        if without_peak == "": file.write("none\n")
        else: file.write(without_peak + "\n" + (max_filename_length + 19) * "=")
        if len(skipped) >= 1: file.write("\n\nSkipped:\n" + skipped)
        file.write(f"\n\n\nParameter" + 38 * " " + "Value\n" + 52 * "=" + "\n2Theta range (in degrees)" + 16 * " " + "{:>11}".format(f"{min_2theta}-{max_2theta}") + "\nNormalized peak detection limit" + 10 * " " + "{:>11}".format(peak_threshold) + "\nMinimum relative peak intensity over mean" + "{:>11}".format(over_mean) + "\nMinimum peak distance (in degrees)" + 7 * " " + "{:>11}".format(min_distance) + "\nMinimum counts" + 27 * " " + "{:>11}".format(background) + "\n" + 52 * "=" + "\n\n\nISoD Sorts Diffractograms\n© Copyright 2017 Alexander M. Puetz (a.puetz@fkf.mpg.de), Department Nanochemistry, Max Planck Institute for Solid State Research, Heisenbergstr. 1, 70569 Stuttgart, Germany")

    print("\nFinished successfully! Results saved in Results.txt and files sorted.\n" + 69 * "_")
    exit = input("\nPress any key to quit...")


if __name__ == '__main__':
    main()
