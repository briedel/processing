#!/usr/bin/env python

import argparse
import csv
import glob
import math
import os
import sys
import time

submit_template_preamble = '''
executable     = run_pax.sh
universe       = vanilla

Error   = log/err.$(Cluster).$(Process)
Output  = log/out.$(Cluster).$(Process)
Log     = log/log.$(Cluster).$(Process)

Requirements = (CVMFS_oasis_opensciencegrid_org_TIMESTAMP >= 1449684749) && (OpSysAndVer =?= "SL6") && \\
               (GLIDEIN_ResourceName =!= "BNL-ATLAS") && (GLIDEIN_ResourceName =!= "AGLT2")

transfer_executable = True
transfer_output_files = results
when_to_transfer_output = ON_EXIT
'''

submit_template_repeats = '''
transfer_input_files= user_cert, CONFIG_FILE

arguments = PAX_VERSION XED_INPUT OUTPUT_FILES CONFIGURATION
queue 1
'''


def get_xed_files(run, data_set, info_directory):
    """
    Return a list of xed files belonging to a given run and dataset
    using csv files in the info_directory

    :param run:            run to process
    :param data_set:       dataset in the run to process,
                           'all' indicates all datasets
    :param info_directory: directory with csv files with info on files
    :return: a list of paths to xed files to process
    """
    xed_files = []
    csv_files = []
    if not os.path.isdir(info_directory):
        sys.stderr.write("{0} is not a directory, exiting".format(info_directory))
        sys.exit(1)
    if data_set == 'all':
        for entry in glob.glob(os.path.join(info_directory, "{0}_*_files.csv".format(run))):
            csv_files.append(os.path.join(entry))
    else:
        csv_files = [os.path.join(info_directory, "{0}_{1}_files.csv".format(run, data_set))]
    for entry in csv_files:
        xed_files.extend(read_file(entry))
    return xed_files


def read_file(filename):
    """
    Read a csv file with run/data set info and return xed files for it

    :param filename: csv file to process
    :return: a list of xed files
    """
    if not os.path.isfile(filename):
        return []
    with open(filename) as file_obj:
        xed_files = []
        csv_reader = csv.reader(file_obj)
        header = True
        for row in csv_reader:
            if header:
                # Skip header row
                header = False
                continue
            xed_files.append(row[2])
        return xed_files


def run_main():
    """
    Main function to process user input and then generate the appropriate submit files

    :return: exit code -- 0 on success, 1 otherwise
    """

    parser = argparse.ArgumentParser(description="Setup submit files for processing xenon100 files using PAX")
    parser.add_argument('--run', dest='run',
                        action='store', default='',
                        help='run to process')
    parser.add_argument('--dataset', dest='data_set',
                        action='store', default='',
                        help='dataset in run to process (use "all" to '
                             'process all datasets')
    parser.add_argument('--info-directory', dest='info_directory',
                        action='store', default='',
                        help='path to directory with information on runs '
                             'and datasets')
    parser.add_argument('--batch-size', dest='batch_size',
                        action='store', default=15, type=int,
                        help='number of files to process per job (default is 15)')
    parser.add_argument('--pax-version', dest='pax_version',
                        action='store', required=True,
                        help='pax version (must be pre-installed on OASIS/OSG)')
    parser.add_argument('--config', dest='config',
                        action='store', required=True,
                        help='pax configuration (or specify .ini file in working directory for custom config)')

    args = parser.parse_args(sys.argv[1:])

    # Load lists of .xed files
    xed_files = get_xed_files(args.run, args.data_set, args.info_directory)
    if len(xed_files) == 0:
        sys.stdout.write("No files to process, exiting \n")
        return 0

    # Check for active GRID certificate
    if not os.path.isfile('user_cert'):
        sys.stderr.write("No user proxy found, please generate one using \n" +
                         "voms-proxy-init  -voms xenon.biggrid.nl " +
                         "-valid 168:00 -out user_cert \n")
        sys.exit(1)

    num_jobs = int(math.ceil(len(xed_files) / float(args.batch_size)))

    sys.stdout.write("Processing {0} files using {1} jobs\n".format(len(xed_files), num_jobs))
    #sys.stdout.write("Proceeding in 10 seconds\n")
    sys.stdout.flush()
    #time.sleep(10)

    # Create job submission file
    output = open("process_run.submit", 'w')
    output.write(submit_template_preamble)

    # Loop over number of jobs
    for job in range(0, num_jobs):
        lower_index = job * args.batch_size
        upper_index = (job + 1) * args.batch_size
        input_file_paths = []
        output_files = []
        if upper_index >= len(xed_files):
            upper_index = len(xed_files)

        file_config = []

        # Loop over files in batch
        for index in range(lower_index, upper_index):
            input_filename = os.path.split(xed_files[index])[1]
            output_files.append(input_filename.replace(".xed", "_pax"+args.pax_version))
            input_file_paths.append(xed_files[index])
            file_config.append(args.config)

        # Detatils for batch
        text_buffer = submit_template_repeats
        text_buffer = text_buffer.replace('PAX_VERSION', args.pax_version)
        text_buffer = text_buffer.replace('OUTPUT_FILES', ",".join(output_files))
        text_buffer = text_buffer.replace('XED_INPUT', ",".join(input_file_paths))
        text_buffer = text_buffer.replace('CONFIGURATION', ",".join(file_config))
      
        # For transferring custom config file
        if ".ini" in args.config:
            text_buffer = text_buffer.replace('CONFIG_FILE', args.config)
        else:
            text_buffer = text_buffer.replace('CONFIG_FILE',"")

        output.write(text_buffer)

    if not os.path.exists('results'):
        os.mkdir('results')
    if not os.path.exists('log'):
        os.mkdir('log')

    return 0

if __name__ == '__main__':
    sys.exit(run_main())
