########################################################
## Code for batching the merge processes
## It will merge every file that appear under truth root path
## which has a corresponding file under processed root path
########################################################
#!/usr/bin/python
import sys, array, os, getpass
from subprocess import call
import subprocess as subp
import time
import math as math
import glob
from subprocess import Popen, PIPE

if len(sys.argv)<=1:
    print("======== Usage =========")
    print("python BatchMergeTruthAndProcessed.py <config file> <truth csv path> <processed root path> <output path> <(opt)relative path for submission> <(opt) if use public node (1) optional (2 for use kicp nodes)> <(opt)Submit ID> <(opt) if use arrays in output (1) (default 0)> <(opt) minitree type; 0(default): Basics, 1: S1S2Properties, 2: PeakEfficiency> <(opt) save afterpulses in arrays (default 0)>")
    exit()

CurrentEXE = sys.argv[0]
ConfigFile = sys.argv[1]
TruthCSVPath = sys.argv[2]
ProcessedRootPath = sys.argv[3]
OutputPath = sys.argv[4]
IfPublicNode = 1
RelativeSubmitPath = "Submit"
if len(sys.argv)>5:
    RelativeSubmitPath = sys.argv[5]
if len(sys.argv)>6:
    IfPublicNode = int(sys.argv[6])
SubmitID = 0
if len(sys.argv)>7:
    SubmitID = int(sys.argv[7])
ArrayOutput = 0
if len(sys.argv)>8:
    ArrayOutput = int(sys.argv[8])
MinitreeType=0
if len(sys.argv)>9:
    MinitreeType = int(sys.argv[9])
if len(sys.argv)>10:
    save_ap = sys.argv[10]


#######################
## Define the exe1&2
########################
MaxNumJob = 64
if not IfPublicNode:
    MaxNumJob=200
CurrentPath = os.getcwd()
CurrentUser = getpass.getuser()
EXE_Path = CurrentEXE.split("BatchMergeTruthAndProcessed.py")[0]
if ArrayOutput==1:
    EXE1 = CurrentPath+"/"+EXE_Path+"TruthSorting_arrays.py"
else:
    EXE1 = CurrentPath+"/"+EXE_Path+"TruthSorting.py"
if MinitreeType==2:
    EXE2 = CurrentPath+"/"+EXE_Path+"MergeTruthAndProcessed_peaks.py"
else:
    EXE2 = CurrentPath+"/"+EXE_Path+"MergeTruthAndProcessed.py"


#######################
## Get the list 
#######################
FileList = glob.glob(TruthCSVPath+"/*.csv")
# trail to IDList
IDList = []
for filename in FileList:
    ID = filename.split("FakeWaveform_XENON1T_")[1].split("_truth.csv")[0]
    IDList.append(ID)

# create temporary directory
TmpPath = OutputPath+"/TmpFolder_"+str(SubmitID)
if os.path.exists(TmpPath):
    subp.call("rm -r "+TmpPath, shell=True)
subp.call("mkdir "+TmpPath, shell=True)

######################
## Submission
######################
for j, ID_job in enumerate(IDList):
    # create submit directory
    SubmitPath = CurrentPath + "/" +RelativeSubmitPath + "/" + str(j) + "_" + str(SubmitID)
    if RelativeSubmitPath[0]=='/':
        SubmitPath = RelativeSubmitPath + "/" + str(j) + "_" + str(SubmitID)
    if os.path.exists(SubmitPath):
        subp.call("rm -r "+SubmitPath, shell=True)
    subp.call("mkdir "+SubmitPath, shell=True)
    # create submit file
    SubmitFile = SubmitPath + "/submit"
    if os.path.exists(SubmitFile):
        subp.call("rm "+SubmitFile, shell=True)
    # start to fill the submitted job
    OneProcessedFile = glob.glob(ProcessedRootPath+"/FakeWaveform_XENON1T_"+ID_job+"*.root")
    if len(OneProcessedFile)==0:
        continue
    ProcessedRootFilename = OneProcessedFile[0]
    TruthCSVFilename = TruthCSVPath+"/FakeWaveform_XENON1T_"+ID_job+"_truth.csv"
    TmpOutputFilename = TmpPath+"/FakeWaveform_XENON1T_"+ID_job+"_tmp.pkl"
    OutputFilename = OutputPath+"/FakeWaveform_XENON1T_"+ID_job+"_merged.pkl"
    AbsoluteConfigFile = CurrentPath+"/"+ConfigFile
    if len(ProcessedRootFilename)<2 or len(TruthCSVFilename)<2:
        continue
    print("To process -> "+ID_job)
    # create the submit 
    subp.call("echo '#!/bin/bash\n' >> "+SubmitFile, shell=True)
    subp.call("echo '#SBATCH --output="+SubmitPath+"/myout_"+str(SubmitID)+"_"+str(j)+".txt \n' >> "+SubmitFile, shell=True)
    subp.call("echo '#SBATCH --error="+SubmitPath+"/myerr_"+str(SubmitID)+"_"+str(j)+".txt\n' >> "+SubmitFile, shell=True)
    subp.call("echo '#SBATCH --time=00:05:00\n' >> "+SubmitFile, shell=True)
    if not IfPublicNode:
        subp.call("echo '#SBATCH --account=pi-lgrandi\n' >> "+SubmitFile, shell=True)
        subp.call("echo '#SBATCH --qos=xenon1t\n' >> "+SubmitFile, shell=True)
        subp.call("echo '#SBATCH --partition=xenon1t\n' >> "+SubmitFile, shell=True)
    elif IfPublicNode==2:
        subp.call("echo '#SBATCH --account=pi-lgrandi\n' >> "+SubmitFile, shell=True)
        subp.call("echo '#SBATCH --qos=xenon1t-kicp\n' >> "+SubmitFile, shell=True)
        subp.call("echo '#SBATCH --partition=kicp\n' >> "+SubmitFile, shell=True)
    subp.call("echo '. /home/mcfate/Env/GlobalPAXEnv.sh\n\n' >> "+SubmitFile, shell=True)
    if ArrayOutput:
        print('running ' + TruthCSVFilename)
        subp.call("echo 'python "+EXE1+" "+TruthCSVFilename+" "+TmpOutputFilename+" 0 "+save_ap+"' >> "+SubmitFile, shell=True)
    else:
        subp.call("echo 'python "+EXE1+" "+TruthCSVFilename+" "+TmpOutputFilename+"' >> "+SubmitFile, shell=True)
    subp.call("echo 'python "+EXE2+" "+AbsoluteConfigFile+" "+TmpOutputFilename+" "+ProcessedRootFilename+" "+OutputFilename+"' >> "+SubmitFile, shell=True)
    
    #submit
    IfSubmitted=0
    while IfSubmitted==0:
        Partition = "sandyb" # public
        if not IfPublicNode:
            Partition = "xenon1t"
        elif IfPublicNode==2:
            Partition = "kicp"
        p1 = Popen(["squeue","--partition="+Partition, "--user="+CurrentUser], stdout=PIPE)
        p2 = Popen(["wc", "-l"], stdin=p1.stdout, stdout=PIPE)
        p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
        output = p2.communicate()[0]
        Status=subp.call("squeue --partition="+Partition+" --user=mcfate | wc -l", shell=True)
        Output=int(output)
        #print(Status)
        print("Current job running number "+str(Output))            
        if Status==0 and Output<MaxNumJob:
            #sbatch it 
            subp.call("cd "+SubmitPath+";sbatch "+SubmitFile+";cd -", shell=True)
            IfSubmitted=1   
            subp.call("rm "+SubmitFile, shell=True) 
            time.sleep(1)
        else:
            time.sleep(30) 


# delete the temporary path
subp.call("rm -rf "+TmpPath, shell=True)
