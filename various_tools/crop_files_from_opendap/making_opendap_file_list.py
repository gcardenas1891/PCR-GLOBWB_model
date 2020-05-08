#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import shutil

def main():
    
    local_source_folder = "/quanta1/home/hydrowld/data/hydroworld/pcrglobwb2_input_release/version_2019_11_beta/pcrglobwb2_input/"

    opendap_main_folder = "https://opendap.4tu.nl/thredds/dodsC/data2/pcrglobwb/version_2019_11_beta/pcrglobwb2_input/"
    
    for roots, dirs, files in os.walk(local_source_folder, followlinks = True):

        for file_name in files:
            
            print("\n\n")

            # local file name
            local_file_name = os.path.join(roots, file_name)
            
            # opendap file name
            opendap_filename = local_file_name.replace(local_source_folder, opendap_main_folder)

            # print only netcdf files and skip cloneMaps directories
            if (target_file_name.endswith(".nc") or target_file_name.endswith(".nc4")) and ("cloneMaps" not in target_file_name):

                print(target_file_name)
                
                # write it to the file

    print("\n Done! \n")                          
                                        

if __name__ == '__main__':
    sys.exit(main())
