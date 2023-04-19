__author__ = "Alexander M. Puetz, M.Sc."
__date__ = "$2021-05-05$"

import pandas as pd
import os
import sys
import glob
import numpy as np
import time
from io import StringIO

"""Search list of str for first occurence of a substring and return index of that str"""
def find_snippet(lines, snippet):
    indices, i = [], 0
    while i < len(lines): #iterate over all str in list
        if lines[i].find(snippet) > -1: indices.append(i) #str.find returns -1 if substring not in str, thus all results >-1 contain substring somewhere
        i += 1
    return indices[0] #return only the first occurence

"""Open file and extract all neccessary data"""
def extract_data_from_file(file, detector):
    global experiment, analytes
    with open(file,'r') as text_file: text_file = open(file, "r")
    report = text_file.read()
    lines = report.split("\n") #create list of str, where each is a line of the txt file
    
    data = {}
    for snippet in ["Acquired", "Sample Name", "Sample ID", "Detector Name"]: #extract parameters and save in dict
        line = lines[find_snippet(lines, snippet)]
        data[snippet] = line.split("\t")[-1]
    if data["Detector Name"] != detector: return #check if measured by TCD or BID
    else: del data["Detector Name"] #drop now unnecessary entry from dict and continue

    results_table = lines[find_snippet(lines, "[Compound Results(Ch1)]"):] #truncate file to last few lines containing BID data
    first_line = find_snippet(results_table,"# of IDs")+1
    results_table = results_table[first_line:] #truncate to table only
    results_table_new = ""
    for line in results_table: #reformat each line to be CSV-like
        line = line.replace(",",".")
        line = line.replace("\t", ";")
        if line != "": results_table_new += line+"\n" #add non-empty lines to new str
    results_table = results_table_new
    df = pd.read_csv(StringIO(results_table), sep=";")
    df = df[['Name', 'Conc.']] #read str into df and drop unnecessary columns
    analytes = []
    for row in range(len(df)):
        data[df.iat[row,0]+" (ppm)"] = df.iat[row,1] #add entries to dictionary where Name is key and Conc. is value
        analytes.append(df.iat[row,0]+" (ppm)")
    
    print("Reading in "+file)
    return pd.Series(data) #return as series


"""Read all reports in the specified folder, extract data and save in table"""
def read_folder(directory, detector):
    #create file list
    filenames = []
    for file in sorted(glob.glob(directory+"*.txt")): filenames.append(file)
    if len(filenames) == 0:
        print("No files found. Quitting...")
        time.sleep(2)
        exit()
    savename = directory+"data_"
    
    #read in all files and collect in a single dataframe
    experiment_data = pd.DataFrame()
    for file in filenames:
        data = pd.DataFrame()
        data = data.append(extract_data_from_file(file,detector),ignore_index=True) #convert Series into DataFrame
        if len(data) == 1: #only include non-empty data created from files measured by specified detector
            experiment_data = pd.concat([experiment_data, data],ignore_index=True) #combine all results into one df
    print("Directory read. Beginning data processing...")

    #calculate time since experiment start for each measurement and add to dataframe
    aquired, time = pd.to_datetime(experiment_data['Acquired'],format= '%d.%m.%Y %H:%M:%S'), []
    for i in range(0,len(aquired)): 
        delta = aquired[i] - aquired[0]
        time.append(int(pd.Timedelta(delta, unit='minutes').total_seconds()/60))
    experiment_data.insert(1, 'Time (min)', time)

    #add tags to each data point warning of sampling loss (needed for calculation of activity if using batch mode) or carry-over
    experiment_data['Sampling loss'] = 0
    experiment_data['Carry-over'] = 0
    for i in range(1,len(experiment_data)):
        if experiment_data['Sample ID'].to_list()[i] != experiment_data['Sample ID'].to_list()[i-1]: experiment_data.at[i,'Sampling loss'] = 1
        for analyte in analytes:
            if 0 < experiment_data[analyte].to_list()[i] < experiment_data[analyte].to_list()[i-1] / 1000: 
                experiment_data.at[i,'Carry-over'] = 1
                print("    Warning: Possible sample carry-over detected! Check previous sample in data_"+detector[:-1]+"_all.csv")

    #save all
    print("Processing complete.")
    experiment_data.to_csv(savename+detector[:-1]+"_all.csv", index=False)
    print("Saved "+savename+detector[:-1]+"_all.csv")

    #split results into samples and save individually
    sample_data = [y for x, y in experiment_data.groupby('Sample ID', as_index=False)]
    for i, df in enumerate(sample_data): 
        sample_id = df['Sample ID'].to_list()[0]
        df.drop('Sample ID',axis='columns', inplace=True)
        df.to_csv(savename+detector[:-1]+"_ID_"+str(sample_id)+".csv", index=False)
        print("Saved "+savename+detector[:-1]+"_ID_"+str(sample_id)+".csv")

def main():
    print("\nWelcome! This script will process data measured by GC-2030, sort it by sample, and save it out. \nPlease start by providing the data directory.")
    directory = str("Z:\\GCTCDBID\\"+input("\nZ:\\GCTCDBID\\")+"\\")
    if os.path.isdir(directory) == False: 
        print("Invalid path. Quitting...")
        time.sleep(2)
        exit()

    print("\nProcessing BID data...")
    read_folder(directory, "BID1")
    print("\nProcessing TCD data...")
    read_folder(directory, "TCD1")

    print("\nFinished. Quitting...\n© Alexander M. Pütz and Hugo A. Vignolo-González, 2021")
    time.sleep(2)
    exit()

if __name__ == "__main__":
    main()