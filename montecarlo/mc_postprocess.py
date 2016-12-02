#!/usr/bin/env python
import argparse
import sys
import os
import re
import subprocess

import ROOT

EVENT_THRESHOLD = 0.05
MINITREE_OUTPUTS = {'Basics': 'Basics.root',
                    'Fundamentals': 'Fundamentals.root',
                    'DoubleScatter': 'DoubleScatter.root',
                    'LargestPeakProperties': 'LargestPeakProperties.root',
                    'TotalProperties': 'TotalProperties.root'}


def get_dag_information(dag_filename):
    """
    Parse dag file and get number of jobs in dag

    :return: (jobs, events, flavor) - number of jobs and events and mc type
    """
    jobs = 0
    events = 0
    flavor = None
    event_match = re.compile(r'events="(\d+)"')
    flavor_match = re.compile(r'flavor="(.*?)"')
    if not os.path.isfile(dag_filename):
        sys.stderr.write("{0} not found\n".format(dag_filename))
        return jobs, events
    with open(dag_filename, 'r') as dag_file:
        for line in dag_file:
            if line.startswith('JOB'):
                jobs += 1
            match = event_match.search(line)
            if match:
                events += int(match.group(1))
        dag_file.seek(0)
        match = flavor_match.search(dag_file.read(1024))
        if match:
            flavor = match.group(1)
    return jobs, events, flavor


def merge_files(file_list, result_dir):
    """

    :param file_list: list with root files to merge
    :param result_dir: path to directory to place results in
    :return: True on success, False otherwise
    """
    sample_file = file_list[0]
    fields = sample_file.split('_')
    del fields[3]
    output_file = "_".join(fields)
    command_line = ['hadd', output_file]
    command_line.extend(file_list)
    try:
        subprocess.check_call(command_line)
    except subprocess.CalledProcessError:
        sys.stderr.write("Can't combine files into {0}\n".format(file_list))
        return False
    if not os.path.isdir(result_dir):
        sys.stderr.write("{0} not present\n".format(result_dir))
        return False
    if not os.path.isfile(output_file):
        sys.stderr.write("{0} not present, couldn't ".format(output_file) +
                         "merge files\n")
        return False
    try:
        os.rename(output_file, os.path.join(result_dir, output_file))
    except IOError as e:
        sys.stderr.write("Got exception while moving results: {0}\n".format(e))
        return False
    except OSError as e:
        sys.stderr.write("Got exception while moving results: {0}\n".format(e))
        return False
    return True


def run_main():
    parser = argparse.ArgumentParser(description="Postprocess results generated by mc_process")
    parser.add_argument('--dagfile-file', dest='dag_file',
                        action='store', default='mc.dag',
                        help='file to write dag to')
    args = parser.parse_args(sys.argv[1:])
    jobs, events, flavor = get_dag_information(args.dag_file)
    if events == 0:
        sys.stdout.write("No events generated by this dag file\n")
        return 1
    if jobs == 0:
        sys.stdout.write("No jobs run by this dag file\n")
        return 1

    cur_dir = os.getcwd()
    if not os.path.isdir('output'):
        sys.stderr.write("Output directory not present\n")
        return 1
    os.chdir('output')
    root_files = {'PAX ROOT': ([], 'pax.root')}
    if flavor == 'NEST':
        geant_suffix = 'NEST.root'
        root_files['Patch ROOT'] = ([], 'Patch.root')
    elif flavor == 'G4':
        geant_suffix = 'G4.root'
        root_files['Sort ROOT'] = ([], 'Sort.root')
    elif flavor == 'G4p10':
        geant_suffix = 'G4p10.root'
        root_files['Sort ROOT'] = ([], 'Sort.root')
    else:
        sys.stderr.write("MC flavor unknown: {0}\n".format(flavor))
        return 1

    root_files['Geant ROOT'] = ([], geant_suffix),
    for entry, suffix in MINITREE_OUTPUTS:
        root_files[entry] = ([], suffix)

    for entry in os.listdir('.'):
        for root_type in root_files:
            if entry.endswith(root_files[root_type][1]):
                root_files[root_type][0].append(entry)

    for entry in root_files:
        if len(root_files[entry][0]) != jobs:
            sys.stderr.write("Number of {0} files doesn't".format(entry) +
                             "match the number of jobs: "
                             "{0} vs {1}\n".format(len(root_files[entry][0]),
                                                   jobs))
            sys.stderr.write("An error probably occurred while processing.\n")
            return 1

    for output in ['Geant ROOT', 'Sort ROOT', 'Patch ROOT']:
        if output not in root_files:
            continue
        total_events = 0
        for root_file in root_files[output][0]:
            g4_file = ROOT.TFile.Open(root_file)
            g4_file.cd('events')
            root_events = g4_file.Get('events')
            ttree = root_events.Get('events')
            total_events += ttree.GetEntries()

        if abs(events - total_events) > (EVENT_THRESHOLD * float(events)):
            sys.stderr.write("{0} events differs from requested ".format(output) +
                             "events by more than {0}: ".format(EVENT_THRESHOLD) +
                             "got {0} events, expected {1}\n".format(total_events,
                                                                     events))

    total_events = 0
    for root_file in root_files['PAX ROOT'][0]:
        pax_file = ROOT.TFile.Open(root_file)
        ttree = pax_file.Get('tree')
        total_events += ttree.GetEntries()
    if abs(events - total_events) > (EVENT_THRESHOLD * float(events)):
        sys.stderr.write("PAX events differs from requested " +
                         "events by more than {0}: ".format(EVENT_THRESHOLD) +
                         "got {0} events, expected {1}\n".format(total_events,
                                                                 events))
    for output_type in MINITREE_OUTPUTS:
        total_events = 0
        for root_file in root_files[output_type][0]:
            output_file = ROOT.TFile.Open(root_file)
            ttree = output_file.Get(output_type)
            total_events += ttree.GetEntries()
        if abs(events - total_events) > (EVENT_THRESHOLD * float(events)):
            sys.stderr.write("{0} differs from requested ".format(output_type) +
                             "events by more than {0}: ".format(EVENT_THRESHOLD) +
                             "got {0} events, expected {1}\n".format(total_events,

                                                                     events))
    result_dir = os.path.join(cur_dir, 'merged_results')
    os.mkdir(result_dir)

    for output_type in root_files:
        if not merge_files(root_files[output_type][0], result_dir):
            sys.stderr.write("Can't merge {0} files, exiting\n".format(output_type))
            return 1

    os.chdir(cur_dir)
if __name__ == '__main__':
    sys.exit(run_main())