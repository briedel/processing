#################################
## Sub-code used in WF simulation
## It creates a csv file for the input of fax
## by Qing Lin
## @ 2016-09-12
##
## HARDCODE WARNING: The FV dimensions below need to be modified
##                   according to the detector you wish to simulate
##
## Ref: http://xenon1t.github.io/pax/simulator.html#instruction-file-format
## Code: https://github.com/XENON1T/pax/blob/master/pax/plugins/io/WaveformSimulator.py#L244
##
#################################
import sys
import numpy as np
import scipy as sp

if len(sys.argv)<2:
    print("========= Syntax ==========")
    print("python CreateFakeCSV.py ..... ")
    print("<number of events>")
    print("<photon number lower>")
    print("<photon number upper>")
    print("<electron number lower>")
    print("<electron number upper>")
    print("<output file (abs. path)>")
    exit()

NumEvents = int(sys.argv[1])
PhotonNumLower = float(sys.argv[2])
PhotonNumUpper = float(sys.argv[3])
ElectronNumLower = float(sys.argv[4])
ElectronNumUpper = float(sys.argv[5])
OutputFilename = sys.argv[6]

####################################
## Some functions (HARDCODE WARNING):
####################################
def IfPass48kg(x,y,z):
    # check if the x,y,z passing X48kg0
    I = np.power( (z+15.)/14.6, 4.)
    I += np.power( (x**2+y**2)/20000., 4.)
    if I<1:
        return True
    return False

def RandomizeFV():
    # randomize the X, Y, Z according to X48kg FV
    Zlower, Zupper = -14.6-15.0, -14.6+15.0
    Rlower, Rupper = -np.sqrt(200.), np.sqrt(200.)
    for i in range(100000):
        x = np.random.uniform(Rlower,Rupper)
        y = np.random.uniform(Rlower,Rupper)
        z = np.random.uniform(Zlower,Zupper)
        if IfPass48kg(x,y,z):
            return (x,y,z)
    return (0,0,0)


####################################
## Starts to create
####################################
# Some default
DefaultType = "ER"
DefaultEventTime = 10000
##########
fout = open(OutputFilename, 'w')
# headers
fout.write("instruction,recoil_type,x,y,depth,s1_photons,s2_electrons,t\n")
# events loop
for i in range(NumEvents):
    fout.write(str(i)+",")
    fout.write(DefaultType+",")
    X, Y, Z = RandomizeFV()
    #fout.write(str(X)+",")
    #fout.write(str(Y)+",")
    fout.write("random,")
    fout.write("random,")
    fout.write(str(-Z)+",")
    NumPhoton = int( np.random.uniform(PhotonNumLower, PhotonNumUpper) )
    fout.write(str(NumPhoton)+",")
    NumElectron = int( np.random.uniform(ElectronNumLower, ElectronNumUpper) )
    fout.write(str(NumElectron)+",")
    fout.write(str(DefaultEventTime)+"\n")
fout.close()