#!/usr/bin/python
import os
import xml.etree.ElementTree as ET
import uuid
import sys,time,subprocess,socket,logging,stat
import threading,subprocess
import pprint, socket, ssl
from datetime import datetime,timedelta
import __future__
def supported_os_msg():
    print("This script can be run on a machine with below operation systems.")
    print("Ubuntu 12.04 and above")
    print("CentOS 6.5 and above")
    print("RHEL 6.7 and above")
    print("Debian 7 and above")
    print("Oracle Linux 6.4 and above")
    print("SLES 12 and above")
    print("OpenSUSE 42.2 and above")

def exitonconfirmation():
    while True:
        ans=input_for_python_Version("\nPlease enter 'q/Q' to exit...")
        if 'q' in ans or 'Q' in ans:
            sys.exit()

#message should be str as byte array concatenation is no more supported 
def log(message):
    logtime = time.strftime("%Y%m%d-%H%M%S")
    logfile.write(("[" + logtime + "] : " + message))
    logfile.write("\n")

def is_supported(OsVersion, LowestVersion):
    return ((OsVersion - LowestVersion >= 0) or (abs(OsVersion - LowestVersion) <= 0.01 ))

def is_package_installated(package):
    proc = subprocess.Popen(["which " + package], stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    output = proc.stdout.read()
    return True if output else False

def run_shell_cmd(cmd):
    proc = subprocess.Popen([cmd], stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    output_line = bytes_to_str(proc.stdout.read())
    log("Running cmd: " + cmd)
    log(output_line)
    err = bytes_to_str(proc.stderr.read())
    if err:
        log("Got error")
        log(err)

def get_pkg_installer_cmd_from_os(OsName):
    if OsName in ["Debian", "Ubuntu"]:
        installcmd='apt-get --assume-yes install'
    elif OsName in ["CentOS", "Oracle", "RHEL"]:
        installcmd='yum -y install'
    elif OsName in ["SLES", "OpenSUSE"]:
        installcmd='zypper install'
    else:
        installcmd='apt-get --assume-yes install'
    return installcmd

#newly added function to support conversion from byte array to str as returned from the subprocess
def bytes_to_str(byteArray):
    global encoding 
    encoding = "utf-8"
    if type(byteArray) == str:
        return byteArray
    return str(byteArray,encoding)
    
def bytelist_to_strlist(byteList):
    strList = []
    for i in byteList:
        strList.append(bytes_to_str(i))
    return strList

def input_for_python_Version(inputMessage):
    if sys.version_info >= (3,0,0):
        return input(inputMessage)
    else :
        return raw_input(inputMessage)

def get_python_version():
    if sys.version_info >= (3,0,0):
        return "python3"
    else:
        return "python"

def install_packages(OsName, packages):
    pkg_installer_cmd = get_pkg_installer_cmd_from_os(OsName)
    for package in packages:
        if package == "iscsiadm":
            if OsName in ["CentOS", "Oracle", "RHEL"]:
                installcmd = pkg_installer_cmd + " iscsi-initiator-utils"
            else:
                installcmd = pkg_installer_cmd + " open-iscsi"
        else:
            installcmd = pkg_installer_cmd + " " + ("acl" if package == "setfacl" else package)
        p = subprocess.Popen([installcmd],shell=True)
        p.wait()
        p = subprocess.Popen(["which " + package],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        output = bytes_to_str(p.stdout.read())
        err = bytes_to_str(p.stderr.read())
        log(package +" installation output:"+output+".")
        log(package +" installation Error:"+err)
        if err and not err.isspace():
            log("Failed to install " + package)
            print("Failed to install " + package)
            print("Error Details : .%s." % (err))
            exitonconfirmation()

def install_prereq_packages(OsName):
    packages = ["setfacl", "iscsiadm", "lshw"]
    package_map = {}
    for package in packages:
        package_map[package] = is_package_installated(package)
    #todo : need to check of the older lambda works 
    packages_not_installed = list([package for package in list(package_map.keys()) if package_map[package] == False])
    if len(packages_not_installed) > 0:
        pkg_msg = ",".join(["'" + package + "'" for package in packages_not_installed])
        if OsName in ["CentOS", "Oracle", "RHEL"]:
            pkg_msg = pkg_msg.replace("iscsiadm", "iscsi-initiator-utils")
        else:
            pkg_msg = pkg_msg.replace("iscsiadm", "open-iscsi")
        print("The script requires " + pkg_msg + " to run")
        print("Do you want us to install " + pkg_msg + " on this machine?")
        ans=input_for_python_Version("Please press 'Y' to continue with installation, 'N' to abort the operation. : ")
        if ans in ['y','Y']:
            install_packages(OsName, packages_not_installed)
        elif ans in ['n','N']:
            log("Aborting Installation...")
            print("Aborting Installation...")
            print("Please install " + pkg_msg + " and then run this script again.")
            exitonconfirmation()
        else:
            log("You have entered invalid input.:"+ans)
            print("You have entered invalid input. Please try re-running the script.")
            exitonconfirmation()


def install_prereq_packages_for_securetcptunnel():
    """
    Check if asyncore is available, if not, offer to install pyasyncore
    This is specifically for SecureTCPTunnel functionality
    """
    log("Checking asyncore availability for SecureTCPTunnel...")
    print("Checking asyncore availability for SecureTCPTunnel...")
    
    # Check if asyncore is available
    try:
        import asyncore
        log("asyncore is available - SecureTCPTunnel can proceed")
        print("asyncore is available - SecureTCPTunnel can proceed")
        return True
    except ImportError:
        log("asyncore is not available")
        print("asyncore is not available (likely Python 3.12+)")
        
        # Ask user if they want to install pyasyncore
        print("\nThe SecureTCPTunnel component requires 'asyncore' module which was removed in Python 3.12+")
        print("We can install 'pyasyncore' as a replacement that provides the same functionality.")
        ans = input_for_python_Version("Do you want us to install 'pyasyncore' Python package? ('Y'/'N'): ")
        
        if ans in ['y', 'Y']:
            log("User agreed to install pyasyncore")
            print("Installing pyasyncore Python package...")
            
            # Use apt-get or appropriate package manager to install pyasyncore
            pythonVersion = get_python_version()
            
            # Get the OS information for determining the correct package manager
            osname, _ = GetOsConfigFromReleasesFolder()
            OsName = get_osname_for_script(osname)
            install_cmd = get_pkg_installer_cmd_from_os(OsName)
            
            if pythonVersion == "python3":
                pkg_install_cmd = f"{install_cmd} python3-pyasyncore"
            else:
                pkg_install_cmd = f"{install_cmd} python-pyasyncore"
            
            log(f"Installing pyasyncore using: {pkg_install_cmd}")
            print(f"Installing pyasyncore package using system package manager...")
            
            # Install pyasyncore using the system package manager
            proc = subprocess.Popen([pkg_install_cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.wait()
            output = bytes_to_str(proc.stdout.read())
            err = bytes_to_str(proc.stderr.read())
            log("pyasyncore installation output: " + output)
            log("pyasyncore installation error: " + err)
            
            # Verify the installation worked by trying to import asyncore again
            try:
                import asyncore
                log("asyncore import successful after pyasyncore installation")
                print("pyasyncore installed successfully!")
                print("asyncore is now available - SecureTCPTunnel can proceed")
                return True
            except ImportError:
                log("asyncore still not available after pyasyncore installation")
                print("ERROR: Failed to install pyasyncore successfully")
                print("SecureTCPTunnel requires asyncore module to function.")
                print("Please install pyasyncore manually using your package manager:")
                print("  For Ubuntu/Debian: apt-get install python3-pyasyncore")
                print("  For CentOS/RHEL: yum install python3-pyasyncore")
                print("  For SLES/OpenSUSE: zypper install python3-pyasyncore")
                print("  Or using pip: pip3 install pyasyncore")
                print("Note: pyasyncore provides the asyncore module for Python 3.12+")
                exitonconfirmation()
                return False
                
        else:
            log("User declined to install pyasyncore")
            print("SecureTCPTunnel requires asyncore module to function.")
            print("Please install pyasyncore manually when ready using your package manager:")
            print("  For Ubuntu/Debian: apt-get install python3-pyasyncore")
            print("  For CentOS/RHEL: yum install python3-pyasyncore")
            print("  For SLES/OpenSUSE: zypper install python3-pyasyncore")
            print("  Or using pip: pip3 install pyasyncore")
            print("Note: pyasyncore provides the asyncore module for Python 3.12+")
            exitonconfirmation()
            return False


def check_for_open_SSL_TLS_v12():
    p=subprocess.Popen("openssl ciphers -v | awk '{print $2}' | sort | uniq",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    output = bytes_to_str(p.stdout.read())
    err = bytes_to_str(p.stderr.read())
    log("openssl output:"+output+".")
    if err:
        log("openssl Error:"+err)
    if err and not err.isspace() and output.isspace():
        log("error in getting cipher lists or no output")
    elif "TLSv1.2" in output:
        log("TLSv1.2 is supported")
    else:
        log("TLSv1.2 is not supported")
        print("Microsoft Azure File Folder Recovery script needs OpenSSL with TLSv1.2 cipher to securely connect to the recovery point in Azure.")
        print("To know whether TLSv1.2 is supported in a OS, run this command.")
        print("openssl ciphers -v | awk '{print $2}' | sort | uniq")
        print("The output should show TLSv1.2")
        exitonconfirmation()

def CheckForRAIDDisks(LogFolder):
    lshwpath=LogFolder+'/Scripts/lshw2.xml'
    lshwoutput = open(lshwpath,'w')
    proc=subprocess.Popen(['lshw -xml -class disk -class volume'],shell=True,stdout=lshwoutput)
    log('process started')
    proc.wait()
    log('process completed')
    log('process write completed')
    lshwoutput.flush()
    lshwoutput.close()
    tree = ET.parse(lshwpath)
    root = tree.getroot()
    VolumeIndex=1
    raidvolumeslist=list()

    global isStorageSpaceExists
    isStorageSpaceExists = False
    for nodes in root:
        id= nodes.attrib.get('id')
        if 'disk' in id:
            isMABILRDisk = False
            vendorname="linux"
            disklogicalname=""
            hasvolumes=False
            for child in nodes:
                #print child.tag
                if child.tag == 'vendor':
                    #print child.tag + " " + child.text
                    vendorname = child.text
                    if vendorname == 'MABILR I' :
                        isMABILRDisk = True
                        log('Found MAB ILR Disk')
                        log('Vendor : ' + vendorname)
                elif child.tag == 'logicalname' :
                    disklogicalname=child.text 
                    log('Disk Logical Name :' + disklogicalname)
                else :
                    childclass= child.attrib.get('class')
                    #print  isMABILRDisk
                    if childclass == 'volume' : 
                        hasvolumes=True
                        description=child.find('description')
                        log("description:"+description.text)
                        logname=child.find('logicalname')
                        if logname != None:
                            log('Logical Volume Name : ' + logname.text)
                            if description.text == "Linux raid autodetect partition" or "LVM" in description.text:
                                raidvolumeslist.append((disklogicalname+"  |  "+logname.text+"  |  "+description.text))

            log("Has Volumes"+str(hasvolumes))
            if hasvolumes == False :
                if nodes.attrib.get('class') == 'volume':
                    log("found LVM attached directly to the disk")
                else:
                    log("found disk without volumes")
                diskxmlstring=bytes_to_str(ET.tostring(nodes))
                if "lvm" in diskxmlstring or "LVM" in diskxmlstring :
                    raidvolumeslist.append((disklogicalname+"  |  -------  |  LVM "))
                    log("Found LVM")

    if len(raidvolumeslist) > 0 :
        isStorageSpaceExists = True
        print("\nPlease find below the logical volume/RAID Array entities present in this machine.")
        print("\n************ Volumes from RAID Arrays/LVM partitions ************")
        print("\nSr.No.  |  Disk  |  Volume  |  Partition Type ")
        i=1
        for voldetail in raidvolumeslist:
            print("\n"+str(i)+")  | "+voldetail)
            i=i+1

def GetOsConfigFromReleasesFolder():
    osname=""
    osversion=""
    proc = subprocess.Popen("egrep '^(VERSION_ID)=' /etc/*-release",stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                shell=True,)
    err = bytes_to_str(proc.stderr.read())
    processoutput=bytelist_to_strlist(proc.stdout.readlines())
    if len(processoutput) > 0:
        osversion = processoutput[0].split("\"")[1].strip()
    proc = subprocess.Popen("egrep '^(NAME)=' /etc/*-release",stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                shell=True,)
    err = bytes_to_str(proc.stderr.read())
    processoutput=bytelist_to_strlist(proc.stdout.readlines())
    if len(processoutput) > 0:
        osname = processoutput[0].split("\"")[1].strip()
    if osname == "" or osversion == "":
        proc = subprocess.Popen("egrep 'release' /etc/*-release",stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
        err = bytes_to_str(proc.stderr.read())
        processoutput=bytelist_to_strlist(proc.stdout.readlines())
        if len(processoutput) > 0:
            procoutput = processoutput[0]
            rindex1 = procoutput.find(":")
            rindex = procoutput.rfind("release")
            osname = procoutput[rindex1+1:rindex-1].strip()
            osversion = procoutput[rindex+7:].strip().split(" ")[0]
    return (osname,osversion)


def UnMountILRVolumes(LogFolder):

    proc = subprocess.Popen(["mount | grep '"+LogFolder+"'"],
                                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,
                                    )
    err = bytes_to_str(proc.stderr.read())
    log("Mount List error:"+err)
    processoutput=bytelist_to_strlist(proc.stdout.readlines())
    log("Mount List Output Len :%d" % (len(processoutput)))
    log("Mount List Output :%s." % (processoutput))
    if len(processoutput) > 0:
        for record in processoutput:
            log("UnMount Record :"+record)
            values = record.split(' ')
            log("UnMount Record :"+values[0])
            proc = subprocess.Popen(["umount '"+values[0]+"'"],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,
                                )
            output = bytes_to_str(proc.stdout.read())
            log("UnMount ouput:"+output)
            err = bytes_to_str(proc.stderr.read())
            log("UnMount error:"+err)

    Activated_VG_file=LogFolder+"/Scripts/Activated_VG.txt"
    try:
        if os.path.exists(Activated_VG_file):
            activatedVG=open(Activated_VG_file,'r+')
            activated_VGs = activatedVG.readlines()
            activated_VGs = " ".join(activated_VGs)
            #print (activated_VGs)
            log("Deactivating VGs")
            if activated_VGs:
                proc=subprocess.Popen(["vgchange -a n "+activated_VGs],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                proc.wait()
                out = bytes_to_str(proc.stdout.read())
                err = bytes_to_str(proc.stderr.read())
                log("Deactivating Output:"+out+".")
                log("Deactivating Error:"+err)
                if err:
                    log("Got error while Deactivating")
                else:
                    log("Deactivated VGs successfully")
                activatedVG.truncate(0)
            activatedVG.close()
    except Exception as e:
        log("Exception raised while deactivating the VGs attached from the previous session.")
        log("Exception: " + e.message)

def logout_targets(target_node_addr):
    proc = subprocess.Popen(["iscsiadm -m session"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    output_lines = bytelist_to_strlist(proc.stdout.readlines())
    err_lines = bytelist_to_strlist(proc.stderr.readlines())
    log("Output:" + str(output_lines))
    log("Error:" + str(err_lines))
    for line in output_lines:
        if target_node_addr in line:
            addr = line.split()
            iscsci_target_addr = [x for x in addr if x.startswith('iqn.2016-01.microsoft.azure.backup')]
            if len(iscsci_target_addr) == 1:
                target_addr = iscsci_target_addr[0].strip()
                proc = subprocess.Popen(["iscsiadm -m node -T "+target_addr+" --logout"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
                output = bytes_to_str(proc.stdout.read())
                err = bytes_to_str(proc.stderr.read())
                log("Logging out target: "+ target_addr)
                log("Output:" + output)
                log("Error:" + err)
                if "successful." in output:
                    log("Logout Succeeded for target:"+ target_addr)

def LVMautomation(LogFolder, OlderVGs):
    try:
        pvsTable=subprocess.Popen(["vgs -o +vguuid"],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        output = bytes_to_str(pvsTable.stdout.read())
        output=list(output.split('\n'))
        del output[0]
        del output[len(output)-1]
        for i in range(len(output)):
            output[i]=list(output[i].split())

        #storing new VGs
        ToRenameVGs = dict()
        for i in range(len(output)):
            if output[i][7] not in OlderVGs:
                ToRenameVGs[output[i][0]] = output[i][7] # VG --> UUID

        #renaming VGs to avoid duplicacy
        RenamedVGs = set()
        NotRenamedVGs = set()
        for VGs in ToRenameVGs:     
            renamed = VGs + "_" + str(time.strftime("%Y%m%d%H%M%S"))
            renaming_cmd = "vgrename "+ ToRenameVGs[VGs] + " " + renamed
            proc=subprocess.Popen([renaming_cmd],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            proc.wait()
            out = bytes_to_str(proc.stdout.read())
            err = bytes_to_str(proc.stderr.read())
            log("Renaming Output:"+out)
            log("Renaming Error:"+err)
            if err and 'successfully' not in out:
                log("Got error while Renaming")
                NotRenamedVGs.add(VGs)
                continue
            else:
                log("Renamed successfully")
                RenamedVGs.add(renamed)

        list_of_VG = " ".join(RenamedVGs)
        list_of_NotRenamedVG = " ".join(NotRenamedVGs)
        list_of_allVG = list_of_VG + " " + list_of_NotRenamedVG
        
        #activating renamed VGs
        proc=subprocess.Popen(["vgchange -a y "+list_of_VG],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        proc.wait()
        out = bytes_to_str(proc.stdout.read())
        err = bytes_to_str(proc.stderr.read())
        log ("Activating Output:"+out)
        log ("Activating Error:"+err)
        if err and 'descriptor' not in err:
            log("Got error while Activating Older VGs")
        else:
            log("Older VGs Activated successfully")
        
        #saving the activated VGs
        Activated_VG_file=LogFolder+"/Scripts/Activated_VG.txt"
        activatedVG=open(Activated_VG_file,'w+')
        activatedVG.write(list_of_allVG)
        activatedVG.close()

        #finding the lv path and mounting lvms
        MountedLVMlist = list()
        NotMountedLVMlist = list()
        LVMIndex = 1
        for volume in RenamedVGs:
            display_cmd = "lvdisplay "+ volume + " | grep -i Path"
            lvTable=subprocess.Popen([display_cmd],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            output = bytes_to_str(lvTable.stdout.read())
            output=list(output.split('\n'))
            del output[len(output)-1]
            for i in range(len(output)):
                output[i]=list(output[i].split())
                
            for i in range(len(output)):
                MountPath = LogFolder + "/LVM" + str(LVMIndex)
                LVMIndex = LVMIndex+1
                os.mkdir(MountPath)
                fschk_cmd = "lsblk -f " + output[i][2]
                fsp=subprocess.Popen(fschk_cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
                fsp.wait()
                out = bytelist_to_strlist(fsp.stdout.readlines())
                err = bytes_to_str(fsp.stderr.read())
                is_error = err or (len(out) != 2)
                if is_error:
                    log("Got error while checking filesystem")
                    log(err)
                    log(str(out))
                    NotMountedLVMlist.append(output[i][2])
                else:
                    file_system_output = out[1].strip().split()
                    if len(file_system_output) > 1 and file_system_output[1]:
                        log("Mounting lvm "+(output[i][2])+" to path "+(MountPath))
                        proc = subprocess.Popen(["mount "+output[i][2]+" "+MountPath],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                        out = bytes_to_str(proc.stdout.read())
                        err = bytes_to_str(proc.stderr.read())
                        log("Mount Output for LVM:"+out)
                        log("Mount Error for LVM:"+err)
                        if err:
                            log("Got error while mounting LVM")
                            NotMountedLVMlist.append(output[i][2])
                        else:
                            log("Mounted LVM with lv path: "+output[i][2])
                            MountedLVMlist.append(output[i][2] + "  |  " + MountPath)
                    else:
                        NotMountedLVMlist.append(output[i][2])
                        log("Found LVM "+output[i][2]+" with no file system.")
        
        for volume in NotRenamedVGs:
            display_cmd = "lvdisplay "+ volume + " | grep -i Path"
            lvTable=subprocess.Popen([display_cmd],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            output = bytes_to_str(lvTable.stdout.read())
            output=list(output.split('\n'))
            del output[len(output)-1]
            for i in range(len(output)):
                output[i]=list(output[i].split())
            for i in range(len(output)):
                NotMountedLVMlist.append(output[i][2])
            
        return MountedLVMlist, NotMountedLVMlist
    
    except Exception as e:
        log("Exception raised while automating the process of mounting LVMs.")
        log("Exception: " + e.message)
        MountedLVMlist = list()
        NotMountedLVMlist = list()
        return MountedLVMlist, NotMountedLVMlist

def MountILRVolumes(LogFolder, OlderVGs, sameMachineRecovery):
    time.sleep(5)
    lshwpath = LogFolder+'/Scripts/lshw1.xml'
    lshwoutput = open(lshwpath,'w')
    proc=subprocess.Popen(['lshw -xml -class disk -class volume'],shell=True,stdout=lshwoutput)
    log('process started')
    proc.wait()
    log('process completed')
    log('process write completed')
    lshwoutput.flush()
    lshwoutput.close()
    tree = ET.parse(lshwpath)
    root = tree.getroot()
    VolumeIndex = 1
    volumeslist = list()
    raidvolumeslist = list()
    failedvolumeslist = list()
    LVMlist = list()
    LVlist = list()
    for nodes in root:
        id= nodes.attrib.get('id')
        if 'disk' in id:
            isMABILRDisk = False
            vendorname = "linux"
            disklogicalname = ""
            hasvolumes = False
            for child in nodes:
                #print child.tag
                if child.tag == 'vendor':
                    #print child.tag + " " + child.text
                    vendorname = child.text
                    if vendorname == 'MABILR I':
                        isMABILRDisk = True
                        log('Found MAB ILR Disk')
                        log('Vendor : ' + vendorname)
                elif child.tag == 'logicalname' and isMABILRDisk :
                    disklogicalname=child.text  
                    log('Disk Logical Name :' + disklogicalname)
                else :
                    childclass = child.attrib.get('class')
                    #print  isMABILRDisk
                    if childclass == 'volume' and isMABILRDisk :
                        hasvolumes=True
                        description=child.find('description')
                        log("description:"+description.text)
                        logname=child.find('logicalname')
                        if logname != None:
                            log('Logical Volume Name : ' + logname.text)
                            if description.text == "Linux raid autodetect partition": 
                                raidvolumeslist.append((disklogicalname+"  |  "+logname.text+"  |  "+description.text))
                            elif "LVM" in description.text:
                                log("disklogicalname  |  logname.text |  description.text")
                                log(disklogicalname+"  |  "+logname.text+"  |  "+description.text)
                                LVMlist.append(logname.text)
                                LVlist.append((disklogicalname+"  |  "+logname.text+"  |  "+description.text))
                            else:
                                MountPath = LogFolder+'/Volume'+str(VolumeIndex)
                                VolumeIndex = VolumeIndex+1
                                log(MountPath)
                                os.mkdir(MountPath)
                                log("Mounting volume"+(logname.text)+" to path "+(MountPath))
                                proc = subprocess.Popen(["mount",logname.text,MountPath],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                                output = bytes_to_str(proc.stdout.read())
                                err = bytes_to_str(proc.stderr.read())
                                log("Mount Output:"+output+".")
                                log("Mount Error:"+err)
                                if err and not err.isspace():
                                    log("Mount failed for volume"+(logname.text)+" to path "+(MountPath))
                                    log("Retry: Mounting with nouuid option for volume"+(logname.text)+" to path "+(MountPath))
                                    proc = subprocess.Popen(["mount","-o","nouuid",logname.text,MountPath],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                                    output = bytes_to_str(proc.stdout.read())
                                    err = bytes_to_str(proc.stderr.read())
                                    log("Mount Output:"+output+".")
                                    log("Mount Error:"+err)
                                    if err and not err.isspace():
                                        log("Retry mount failed for volume"+(logname.text)+" to path "+(MountPath))
                                        failedvolumeslist.append((disklogicalname+"  |  "+logname.text+"  |  "+description.text))
                                    else:
                                        volumeslist.append((disklogicalname+"  |  "+logname.text+"  |  "+MountPath))
                                else:
                                    volumeslist.append((disklogicalname+"  |  "+logname.text+"  |  "+MountPath))
            log("Has Volumes"+str(hasvolumes))
            if hasvolumes == False and isMABILRDisk :
                if nodes.attrib.get('class') == 'volume':
                    log("found LVM attached directly to the MAB ILR disk")
                    log("disklogicalname  |  -------  |  LVM ")
                    log(disklogicalname+"  |  -------  |  LVM ")
                    LVMlist.append(disklogicalname)
                    LVlist.append((disklogicalname+"  |  -------  |  LVM "))
                else:
                    log("found MAB ILR disk without volumes")
                    diskxmlstring=bytes_to_str(ET.tostring(nodes))
                    if "lvm" in diskxmlstring or "LVM" in diskxmlstring :
                        raidvolumeslist.append((disklogicalname+"  |  -------  |  LVM "))
                        log("Found LVM")
                    else:
                        fschk_cmd = "lsblk -f " + disklogicalname.strip()
                        fsp=subprocess.Popen(fschk_cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
                        fsp.wait()
                        output = bytelist_to_strlist(fsp.stdout.readlines())
                        err = bytes_to_str(fsp.stderr.read())
                        is_error = err or (len(output) != 2)
                        if is_error:
                            log("Got error while checking filesystem on disks without volumes")
                            log(err)
                            log(str(output))
                        else:
                            file_system_output = output[1].strip().split()
                            if len(file_system_output) > 1 and file_system_output[1]:
                                print("\nIdentified the below disk which does not have volumes.")
                                print("\n " + disklogicalname)
                                ans=input_for_python_Version("Please press 'Y' to continue with mouting this disk without volume, 'N' to abort the operation. : ")
                                if ans in ['y','Y']:
                                    MountPath=LogFolder+'/Disk'+str(VolumeIndex)
                                    VolumeIndex=VolumeIndex+1
                                    log(MountPath)
                                    os.mkdir(MountPath)
                                    log("Mounting disk"+(disklogicalname)+" to path "+(MountPath))
                                    proc=subprocess.Popen("mount " + disklogicalname + " " +MountPath,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
                                    output = bytes_to_str(proc.stdout.read())
                                    error = bytes_to_str(proc.stderr.read())
                                    log("Mount Output for Disk without volumes:"+output+".")
                                    log("Mount Error for Disk without volumes:"+error)
                                    if error:
                                        log("Got error while mounting disk without volumes")
                                        log(error)
                                        log("Mount failed for disk"+(disklogicalname)+" to path "+(MountPath))
                                        log("Retry: Mounting with nouuid option for disk"+(disklogicalname)+" to path "+(MountPath))
                                        proc = subprocess.Popen("mount -o nouuid " + disklogicalname + " " + MountPath,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
                                        output = bytes_to_str(proc.stdout.read())
                                        err = bytes_to_str(proc.stderr.read())
                                        log("Mount Output:"+output+".")
                                        log("Mount Error:"+err)
                                        if err and not err.isspace():
                                            log("Retry mount failed for volume"+(disklogicalname)+" to path "+(MountPath))
                                            failedvolumeslist.append((disklogicalname+"  |             |  "+description.text))
                                        else:
                                            volumeslist.append((disklogicalname+"  |             |  "+MountPath))
                                    else:
                                        log("Mounted disklogicalname")
                                        log(disklogicalname)
                                        volumeslist.append(disklogicalname + "  |             |  " + MountPath)

    MountedLVMlist = list()
    NotMountedLVMlist = list()
    
    hasLVM = False
    try:
        pvsTable=subprocess.Popen(["vgs -o +vguuid"],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        output = bytes_to_str(pvsTable.stdout.read())
        output=list(output.split('\n'))
        if len(output) > 1:
            del output[0]
            del output[len(output)-1]
        for i in range(len(output)):
            output[i]=list(output[i].split())
        for i in range(len(output)):
            if output[i][7] not in OlderVGs:
                hasLVM = True
                break
    except:
        log("Error occured while checking for LVMs")

    if (hasLVM or len(LVMlist) > 0) and (not sameMachineRecovery):
        print("\nWe now support mounting the LVMs of the recovery point through our script.")
        ans=input_for_python_Version("Do you want us to mount LVMs as well? ('Y'/'N') ")
        if 'y' in ans or 'Y' in ans:
            log("user selected to automate LVM mounting")
            MountedLVMlist, NotMountedLVMlist = LVMautomation(LogFolder, OlderVGs) 
            log("function called")
        else:
            print("\n************ Logical Volumes ************")
            print("\nSr.No.  |  Disk  |  Volume  |  Partition Type ")
            i = 1
            for voldetail in LVlist:
                print("\n"+str(i)+")  | "+voldetail)
                i=i+1
            print("\nRun the following commands to mount and bring the partitions online.")
            print("\nFor LVM partitions:")
            print("\n    $ pvs <volume name as shown above> - To list the volume group names under this physical volume")
            print("\n    $ lvdisplay <volume-group-name from the above command's result> - To list all logical volumes, names and their paths in this volume group")
            print("\n    $ mount <LV path> </mountpath> - To mount the logical volumes to the path of your choice")   

    if len(volumeslist) > 0:
        print("\n************ Volumes of the recovery point and their mount paths on this machine ************")
        print("\nSr.No.  |  Disk  |  Volume  |  MountPath ")
        i = 1
        for voldetail in volumeslist:
            print("\n"+str(i)+")  | "+voldetail)
            i = i+1
    else:
        print("\n0 volumes mounted as volumes are either RAID Arrays or failed to mount.")

    if len(MountedLVMlist) > 0:
        print("\n************ LVMs of the recovery point and their mount paths on this machine ************")
        print("\nSr.No.  |  LV Path  |  MountPath ")
        i = 1
        for lvmdetail in MountedLVMlist:
            print("\n"+str(i)+")  | "+lvmdetail)
            i = i+1

    if len(LVlist) > 0 and sameMachineRecovery:
        print("\n************ Logical Volumes ************")
        print("\nSr.No.  |  Disk  |  Volume  |  Partition Type ")
        i = 1
        for voldetail in LVlist:
            print("\n"+str(i)+")  | "+voldetail)
            i=i+1
        print("\nRun the following commands to mount and bring the partitions online.")
        print("\nFor LVM partitions:")
        print("\n    $ pvs <volume name as shown above> - To list the volume group names under this physical volume")
        print("\n    $ lvdisplay <volume-group-name from the above command's result> - To list all logical volumes, names and their paths in this volume group")
        print("\n    $ mount <LV path> </mountpath> - To mount the logical volumes to the path of your choice")

    if len(raidvolumeslist) > 0:
        print("\n************ Volumes from RAID Arrays ************")
        print("\nSr.No.  |  Disk  |  Volume  |  Partition Type ")
        i = 1
        for voldetail in raidvolumeslist:
            print("\n"+str(i)+")  | "+voldetail)
            i=i+1
        print("\nRun the following commands to mount and bring the partitions online.")
        print("\nFor RAID Arrays:")
        print("\n    $ mdadm --detail --scan (To display details about all raid disks)")
        print("    The relevant RAID disk will be named as '/dev/mdm/<RAID array name in the backed up VM>'")
        print("\n    Use the mount command if the RAID disk has physical volumes")
        print("    $ mount <RAID Disk Path> </mountpath>")
        print("\n    If this RAID disk has another LVM configured in it then follow the same prcedure as outlined above for LVM partitions with the volume name being the RAID Disk name")
    
    if len(failedvolumeslist) > 0:
        print("\nThe following partitions failed to mount since the OS couldn't identify the filesystem.")
        print("\n************ Volumes from unknown filesystem ************")
        print("\nSr.No.  |  Disk  |  Volume  |  Partition Type ")
        i = 1
        for voldetail in failedvolumeslist:
            print("\n"+str(i)+")  | "+voldetail)
            i = i+1

    if len(NotMountedLVMlist) > 0:
        print("\nThe following LVMs failed to mount since the OS couldn't identify the filesystem or some error occured while renaming.")
        print("\n************ LVMs from unknown or no filesystem ************")
        print("\nSr.No.  |  LVM")
        i = 1
        for voldetail in NotMountedLVMlist:
            print("\n"+str(i)+")  | "+voldetail)
            i = i+1
        print("\nRun the following commands to mount and bring the partitions online.")
        print("\nFor LVM partitions:")
        print("\n    $ pvs <volume name as shown above> - To list the volume group names under this physical volume")
        print("\n    $ lvdisplay <volume-group-name from the above command's result> - To list all logical volumes, names and their paths in this volume group")
        print("\n    $ mount <LV path> </mountpath> - To mount the logical volumes to the path of your choice")
        
    if len(LVlist) > 0 and len(MountedLVMlist) == 0 and len(NotMountedLVMlist) == 0:
        print("\nThe following LVMs failed to mount because of unknown exceptions.")
        print("\nSr.No.  |  LVM")
        i = 1
        for voldetail in NotMountedLVMlist:
            print("\n"+str(i)+")  | "+voldetail)
            i = i+1
        print("\nRun the following commands to mount and bring the partitions online.")
        print("\nFor LVM partitions:")
        print("\n    $ pvs <volume name as shown above> - To list the volume group names under this physical volume")
        print("\n    $ lvdisplay <volume-group-name from the above command's result> - To list all logical volumes, names and their paths in this volume group")
        print("\n    $ mount <LV path> </mountpath> - To mount the logical volumes to the path of your choice")
    
    if len(failedvolumeslist) > 0 or len(NotMountedLVMlist) > 0:
        print("\nPlease refer to '"+LogFolder+ "/Scripts/MicrosoftAzureBackupILRLogFile.log' for more details.")
    print("\n************ Open File Explorer to browse for files. ************")

def UpdateISCSIConfig(logfolder,TargetUserName,TargetPassword):
    iscsi_config_file='/etc/iscsi/iscsid.conf'
    iscsi_config_temp_file1=logfolder+"/Scripts/iscsidtemp1.conf"
    iscsi_config_temp_file2=logfolder+"/Scripts/iscsidtemp2.conf"
    iscsiconfig=open(iscsi_config_temp_file1,'w+')
    iscsiconfig.write("discovery.sendtargets.auth.authmethod =\n")
    iscsiconfig.write("discovery.sendtargets.auth.authmethod=\n")
    iscsiconfig.write("discovery.sendtargets.auth.authmethod  \n")
    iscsiconfig.write("discovery.sendtargets.auth.username =\n")
    iscsiconfig.write("discovery.sendtargets.auth.username=\n")
    iscsiconfig.write("discovery.sendtargets.auth.username  \n")
    iscsiconfig.write("discovery.sendtargets.auth.password =\n")
    iscsiconfig.write("discovery.sendtargets.auth.password=\n")
    iscsiconfig.write("discovery.sendtargets.auth.password  \n")
    iscsiconfig.write("discovery.sendtargets.auth.username_in =\n")
    iscsiconfig.write("discovery.sendtargets.auth.username_in=\n")
    iscsiconfig.write("discovery.sendtargets.auth.username_in  \n")
    iscsiconfig.write("discovery.sendtargets.auth.password_in =\n")
    iscsiconfig.write("discovery.sendtargets.auth.password_in=\n")
    iscsiconfig.write("discovery.sendtargets.auth.password_in  \n")
    iscsiconfig.write("node.session.auth.authmethod =\n")
    iscsiconfig.write("node.session.auth.authmethod=\n")
    iscsiconfig.write("node.session.auth.authmethod  \n")
    iscsiconfig.write("node.session.auth.chap_algs =\n")
    iscsiconfig.write("node.session.auth.chap_algs=\n")
    iscsiconfig.write("node.session.auth.chap_algs  \n")
    iscsiconfig.write("node.session.auth.username =\n")
    iscsiconfig.write("node.session.auth.username=\n")
    iscsiconfig.write("node.session.auth.username  \n")
    iscsiconfig.write("node.session.auth.password =\n")
    iscsiconfig.write("node.session.auth.password=\n")
    iscsiconfig.write("node.session.auth.password  \n")
    iscsiconfig.write("node.session.auth.username_in =\n")
    iscsiconfig.write("node.session.auth.username_in=\n")
    iscsiconfig.write("node.session.auth.username_in  \n")
    iscsiconfig.write("node.session.auth.password_in =\n")
    iscsiconfig.write("node.session.auth.password_in=\n")
    iscsiconfig.write("node.session.auth.password_in  \n")
    iscsiconfig.close()
    log("Removing old iscsi config entries.")
    updatediscsiconfig=open(iscsi_config_temp_file2,'w+')
    p=subprocess.Popen(["grep -v -f "+iscsi_config_temp_file1+" "+iscsi_config_file],
                            stdout=updatediscsiconfig,shell=True,
                            )
    p.wait()

    log("Removed old iscsi config entries.")
    updatediscsiconfig.write("\ndiscovery.sendtargets.auth.authmethod = CHAP")
    updatediscsiconfig.write("\ndiscovery.sendtargets.auth.username = "+OSName+TargetUserName)
    updatediscsiconfig.write("\ndiscovery.sendtargets.auth.password = "+TargetPassword)
    updatediscsiconfig.write("\n#discovery.sendtargets.auth.username_in = username_in")
    updatediscsiconfig.write("\n#discovery.sendtargets.auth.password_in = password_in")
    updatediscsiconfig.write("\nnode.session.auth.authmethod = CHAP")
    p = subprocess.Popen(["grep chap_algs "+iscsi_config_file],shell=True,stdout=subprocess.PIPE)
    p.wait()
    output = bytes_to_str(p.stdout.read())
    if output:
        updatediscsiconfig.write("\n#node.session.auth.chap_algs = SHA3-256,SHA256,SHA1,MD5")
    updatediscsiconfig.write("\nnode.session.auth.username = "+OSName+TargetUserName)
    updatediscsiconfig.write("\nnode.session.auth.password = "+TargetPassword)
    updatediscsiconfig.write("\n#node.session.auth.username_in = username_in")
    updatediscsiconfig.write("\n#node.session.auth.password_in = password_in\n")
    log("successfully added new iscsi config entries.")
    updatediscsiconfig.flush()
    updatediscsiconfig.close()
    p=subprocess.Popen(["cp "+iscsi_config_temp_file2+" "+iscsi_config_file],
                            stdout=subprocess.PIPE,shell=True,
                            )
    output = bytes_to_str(p.stdout.read())
    log("CP output:"+output)

    log("/etc/iscsi/iscsid.conf file is replaced successfully.")

def discovery_error_prompt(params):
    err = params['error']
    LogFolder = params['LogFolder']
    TargetNodeAddress = params['TargetNodeAddress']
    TargetPortalAddress = params['TargetPortalAddress']
    TargetPortalPortNumber = params['TargetPortalPortNumber']
    if "initiator failed authorization" in err:
        log("Discovery Failed.")
        print("\nThis script cannot connect to the recovery point. Either the password entered is invalid or the disks have been unmounted.")
        print("Please enter the correct password or download a new script from the portal.")
    elif "iscsid is not running" in err:
        log("Discovery Failed.")
        log("Failure Reason: iscsid is not running")
        print("\nException caught while connecting to the recovery point.")
        print("\nFailure Reason: iscsid is not running. can not connect to iSCSI daemon (111).")
        print("\nPlease refer to the logs at '"+ LogFolder +"/Scripts'. You can also retry running the script from another machine. If problem persists, raise a support request with details about OS of machines where script was run and the entire log folder")
    else:
        log("Discovery Failed.")
        log("Target Not Found :"+TargetNodeAddress)
        log("Unable to acces the target URL : "+TargetPortalAddress+":"+str(TargetPortalPortNumber))
        log("Use below curl command to check the access to any URL and Port")
        log("curl "+TargetPortalAddress+":"+str(TargetPortalPortNumber)+" --connect-timeout 2")
        log("It will display this message if you have access. 'curl: (56) Failure when receiving data from the peer'")
        log("Else it will get timed out with message 'curl: (28) connect() timed out!'")
        print("\nUnable to access Recovery vault, check your proxy/firewall setting to ensure access to <"+TargetPortalAddress+":"+str(TargetPortalPortNumber)+">.")
        print("\nIn general, make sure you meet the network connectivity requirements to Azure Recovery vault as specified here: https://docs.microsoft.com/en-us/azure/backup/backup-azure-vms-prepare#network-connectivity")
        print("\nIf problem persists despite meeting all the network connectivity requirements as specified above, please refer to the logs at '"+ LogFolder +"/Scripts'")

def storeOlderVGs():
    pvsTable=subprocess.Popen(["vgs -o +vguuid"],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    output = bytes_to_str(pvsTable.stdout.read())
    output=list(output.split('\n'))
    if len(output)>0:
        del output[0]
    if len(output)>0:
        del output[len(output)-1]
    for i in range(len(output)):
        output[i]=list(output[i].split())
        #print (output[i])

    OlderVGs = set()
    for i in range(len(output)):
            OlderVGs.add(output[i][7])
    
    return OlderVGs

def ILRMain(ilr_params):
    LogFolder = ilr_params['LogFolder']
    ScriptId = ilr_params['ScriptId']
    MinPort = ilr_params['MinPort']
    MaxPort = ilr_params['MaxPort']
    TargetPortalAddress = ilr_params['TargetPortalAddress']
    TargetPortalPortNumber = ilr_params['TargetPortalPortNumber']
    TargetNodeAddress = ilr_params['TargetNodeAddress']
    TargetUserName = ilr_params['TargetUserName']
    TargetPassword = ilr_params['TargetPassword']
    VMName = ilr_params['VMName']
    MachineName = ilr_params['MachineName']
    docleanup = ilr_params['DoCleanUp']
    global OSName
    OSName = ilr_params['OsNameVersion']
    IsMultiTarget = ilr_params['IsMultiTarget']
    IsPEEnabled = ilr_params['IsPEEnabled']
    LogFileName = LogFolder + "/Scripts/MicrosoftAzureBackupILRLogFile.log"
    IsLargeDisk = ilr_params['IsLargeDisk']

    log("Log Folder Path: " + LogFolder)
    log("Log File Path: " + LogFileName)
    log("Script Id: " + ScriptId)
    log("MinPort: " +  str(MinPort))
    log("MaxPort: " +  str(MaxPort))
    log("TargetPortalAddress: " + TargetPortalAddress)
    log("TargetPortalPortNumber: " + str(TargetPortalPortNumber))
    log("TargetNodeAddress: " + TargetNodeAddress)
    log("IsMultiTarget: " + IsMultiTarget)
    log("IsPEEnabled: " + IsPEEnabled)
    log("IsLargeDisk: " + IsLargeDisk)



    if docleanup:
        log("Only Cleanup called")
        print("\nRemoving the local mount paths of the currently connected recovery point...")

    if TargetPassword == "UserInput012345" and not docleanup :
        TargetPassword=input_for_python_Version("Please enter the password as shown on the portal to securely connect to the recovery point. : ")
        log("Input Password Length: "+str(len(TargetPassword)))
        if len(TargetPassword) != 15 :
            log("Password length is not 15 char. ")
            print("\nYou need to enter the complete 15 character password as shown on the portal screen. Please use the copy button beside the generated password and past here.")
            exitonconfirmation()

    scriptran=False
    isProcessRunning=False
    proc = subprocess.Popen(["tail","-n","1","/etc/MicrosoftAzureBackupILR/mabilr.conf"],
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                        )
    processoutput=bytelist_to_strlist(proc.stdout.readlines())
    log("Output Len :%d" % (len(processoutput)))
    log("Output :%s." % (processoutput))
    if len(processoutput) > 0:
        lastrecord = processoutput[0].split('\n')
        log("Last Record in MABILR Config :%s." % (lastrecord))
        values = lastrecord[0].split(',')
        portnumber=values[4]
        processid=values[5]
        targetnodeaddress=values[3]
        lastvmname=values[6]
        lastlogfolder=values[7]
        scriptran=True
        proc=subprocess.Popen(["iscsiadm -m session"],
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,
                        )
        output = bytes_to_str(proc.stdout.read().lower())
        err = bytes_to_str(proc.stderr.read())
        log("Session Target Output:"+output+".")
        log("Session Target Error:"+err)
        target_address_prefix = targetnodeaddress if IsMultiTarget == "0" else targetnodeaddress[:targetnodeaddress.rfind('.')].lower()
        if target_address_prefix in output:
            if docleanup :
                ans='Y'
            else:
                print("\nWe detected a session already connected to a recovery point of the VM '"+lastvmname+"'.")
                print("We need to unmount the volumes before connecting to the new recovery point of '"+VMName+"'")
                ans=input_for_python_Version("\nPlease enter 'Y' to proceed or 'N' to abort...")

            if 'y' in ans or 'Y' in ans:
                log("Un mounting existing mount points.")
                UnMountILRVolumes(lastlogfolder)
                logout_targets(target_address_prefix)
                if not docleanup:
                    print("\nOlder session disconnected. Establishing a new session for the new recovery point....")
            else:
                print("It is recommended to close the earlier session before starting new connection to another RP.")
                exitonconfirmation()
        else:
            UnMountILRVolumes(lastlogfolder)
    sameMachineRecovery = False
    if not docleanup:
        hostname=socket.gethostname()
        log("Host Name :"+hostname)
        vmname = VMName.split(';')
        if (hostname.lower() == vmname[2].lower() or hostname.lower() == MachineName.lower()):
            sameMachineRecovery = True
            CheckForRAIDDisks(LogFolder)
            log("isStorageSpaceExists"+str(isStorageSpaceExists))
            if isStorageSpaceExists == True :
                print("\nMount the recovery point only if you are SURE THAT THESE ARE NOT BACKED UP/ PRESENT IN THE RECOVERY POINT.")
                print("If they are already present, it might corrupt the data irrevocably on this machine.")
                print("It is recommended to run this script on any other machine with similar OS to recovery files.")
                ans=input_for_python_Version("\nShould the recovery point be mounted on this machine? ('Y'/'N') ")
                if 'y' in ans or 'Y' in ans:
                    log("user selected to continue")
                else:
                    print("\nPlease run this script on any other machine with similar OS to recover files.")
                    exitonconfirmation()
        UpdateISCSIConfig(LogFolder,TargetUserName,TargetPassword)

    if scriptran == True:
        log("Script already ran earlier on this machine.")
        log("PortNumber:%s, PID:%s" % (portnumber,processid))

        proc = subprocess.Popen(["ps","-ww","-o","args","-p",processid],
                        stdout=subprocess.PIPE,
                        )
        processoutput=bytelist_to_strlist(proc.stdout.readlines())
        #print "Output Len :%d" % (len(processoutput))
        #print "Output :%s." % (processoutput)
        if len(processoutput) > 1:
            processname = processoutput[1]  
            log("Process Name :%s." % (processname))
            if processname.find("SecureTCPTunnel") != -1:
                log("SecureTCPTunnel process is already running")
                isProcessRunning=False
                log("Killing the existing SecureTCPTunnelProcess to free 3260 port in OSName:"+OSName)
                proc = subprocess.Popen(["kill","-9",processid],
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE
                        )
                output = bytes_to_str(proc.stdout.read())
                err = bytes_to_str(proc.stderr.read())
                log("Kill output:"+output)
                log("Kill error:"+err)
            else:
                log("SecureTCPTunnel process is not running")
    else:
        log("Script didnt' ran earlier on this machine.")

    if docleanup:
        log("Cleanup Completed")
        print("\nThe local mount paths have been removed.")
        print("\nPlease make sure to click the 'Unmount disks' from the portal to remove the connection to the recovery point.")
        exitonconfirmation()

    if isProcessRunning == False:
        # Check and install prerequisites for SecureTCPTunnel
        if not install_prereq_packages_for_securetcptunnel():
            log("Failed to satisfy SecureTCPTunnel prerequisites - exiting")
            print("Failed to satisfy SecureTCPTunnel prerequisites - exiting")
            exitonconfirmation()
        
        try:
            if "CentOS" in OSName or "Oracle" in OSName or "RHEL" in OSName:
                MinPort=3260
                MaxPort=3260
            log("Starting SecureTCPTunnel process...")
            log("with args:")
            log(LogFolder + "/Scripts/SecureTCPTunnel.py " +  OSName + " " + LogFolder + " " + ScriptId + " " + str(MinPort) + " " + str(MaxPort) + " " + TargetPortalAddress + " " + str(TargetPortalPortNumber) + " " + TargetNodeAddress + " " + VMName)
            pythonVersion = get_python_version()
            proc = subprocess.Popen([pythonVersion , LogFolder + "/Scripts/SecureTCPTunnel.py",OSName,LogFolder,ScriptId,str(MinPort),str(MaxPort),TargetPortalAddress,str(TargetPortalPortNumber),TargetNodeAddress,VMName],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE
                )
            pid=proc.pid
            log("pid : " + str(pid))
        except Exception as e:
            log("Exception raised while starting SecureTCPTunnel process")
            log(repr(e))
            if proc.stdout:
                output = bytes_to_str(proc.stdout.read())
                log("SecureTCPTunnel output:"+output)
            if proc.stderr:
                err = bytes_to_str(proc.stderr.read())
                log("SecureTCPTunnel error:"+err)
        found=True
        maxretrycount=2
        retrycount=0
        while found and retrycount < maxretrycount:
            try:
                time.sleep(1)

                with open('/etc/MicrosoftAzureBackupILR/mabilr.conf','r') as f:
                        lines = bytelist_to_strlist(f.readlines())
                        for line in lines:
                            log(line)
                            values = line.split(',')
                            if values[0] == ScriptId and values[5] == str(pid):
                                log("Secure TCP process added record to config file")
                                found=False
                                portnumber=values[4]
            except Exception as e:
                log("Exception raised while reading mabilr.conf file")
                #log("Exception: "+e.message)
            retrycount=retrycount+1
        if retrycount == maxretrycount:
            log("Secure TCP Process is not started after max retry count")
            if "CentOS" in OSName or "Oracle" in OSName or "RHEL" in OSName:
                print("We are unable to communicate via the port 3260 on this machine since it is being used by ISCSI target server or any other application. Please unblock the port or use another machine where the port is open for communicatoin.")
            else:
                print("We are unable to use local port range "+str(MinPort)+"-"+str(MaxPort)+" for our communication on this machine. Please check if these ports are already being used by another application.")
            print("Please refer to the logs at '"+ LogFolder +"/Scripts'")
            exitonconfirmation()
        else:
            log("SecureTCPTunnel started on  Port %s" % (portnumber))

    print("\nConnecting to recovery point using ISCSI service...")
    log(("Discovering Targets from Portal: "+TargetPortalAddress+","+str(TargetPortalPortNumber)))
    p=subprocess.Popen(["iscsiadm -m discovery -t sendtargets -p 127.0.0.1:"+portnumber],
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,
                            )
    if IsMultiTarget == "0":
        output = bytes_to_str(p.stdout.read())
        err = bytes_to_str(p.stderr.read())
        log("Discovery Output:"+output+".")
        log("Discovery Error:"+err)
        is_blocked = "blocked" in output
        if is_blocked == True:
            print("This vault is Private Endpoint enabled. The script is being run from a machine which is outside the vnet, please run the script from a machine in vnet.")
            exit()
        is_not_ready = "notready" in output
        num_retries_left = 4
        while num_retries_left > 0 and is_not_ready == True:
            print("This is a large disk. The target is not ready yet. Waiting for 5 mins and trying again.")
            log("This is a large disk. The target is not ready yet. Waiting for 5 mins and trying again.")
            time.sleep(300)
            p=subprocess.Popen(["iscsiadm -m discovery -t sendtargets -p 127.0.0.1:"+portnumber],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,
                                )
            output = bytes_to_str(p.stdout.read())
            err = bytes_to_str(p.stderr.read())
            log("Discovery Output:"+output+".")
            log("Discovery Error:"+err)
            is_not_ready = "notready" in output
            num_retries_left = num_retries_left - 1
        if is_not_ready == True:
            print("The target is not ready yet for large disk. Please retry after 10 mins.")
            log("The target is not ready yet for large disk. Please retry after 10 mins.")
            exit()

        if ("127.0.0.1:"+str(portnumber)+",-1 "+TargetNodeAddress) in output:
            log("Discovery Succeeded.")
            log("Target Found: "+TargetNodeAddress)
            log("Connecting to target "+TargetNodeAddress+" ...")
            connection_params = {
                    "TargetNodeAddress" : TargetNodeAddress,
                    "LogFolder" : LogFolder,
                    "LocalPortNumber" : portnumber,
                    "IsMultiTarget" : IsMultiTarget
            }
            OlderVGs = storeOlderVGs()
            connection_status = connect_to_target(connection_params, OlderVGs, sameMachineRecovery)
            if connection_status == False:
                discovery_params = {
                    "error" : err,
                    "LogFolder" : LogFolder,
                    "TargetNodeAddress" : TargetNodeAddress,
                    "TargetPortalAddress" : TargetPortalAddress,
                    "TargetPortalPortNumber" : TargetPortalPortNumber
                }
                discovery_error_prompt(discovery_params)
                
    else:
        output_lines = bytelist_to_strlist(p.stdout.readlines())
        err = bytelist_to_strlist(p.stderr.readlines())
        is_blocked_list = [x for x in output_lines if "blocked" in x.lower()]
        is_blocked = len(is_blocked_list) >= 1
        if is_blocked == True:
            print("This vault is Private Endpoint enabled. The script is being run from a machine which is outside the vnet, please run the script from a machine in vnet.")
            exit()
        log("Discovery Output:"+str(output_lines)+".")
        log("Discovery Error:"+str(err))
        not_ready_list = [x for x in output_lines if "notready" in x.lower()]
        num_retries_left = 4
        while num_retries_left > 0 and len(not_ready_list) >= 1:
            print("This is a large disk. The target is not ready yet. Waiting for 5 mins and trying again.")
            log("This is a large disk. The target is not ready yet. Waiting for 5 mins and trying again.")
            time.sleep(300)
            p=subprocess.Popen(["iscsiadm -m discovery -t sendtargets -p 127.0.0.1:"+portnumber],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,
                                )
            output_lines = bytelist_to_strlist(p.stdout.readlines())
            err = bytelist_to_strlist(p.stderr.readlines())
            log("Discovery Output:"+str(output_lines)+".")
            log("Discovery Error:"+str(err))
            not_ready_list = [x for x in output_lines if "notready" in x.lower()]
            num_retries_left = num_retries_left - 1
        if len(not_ready_list) >= 1:
            print("The target is not ready yet for large disk. Please retry after 10 mins.")
            log("The target is not ready yet for large disk. Please retry after 10 mins.")
            exit()
        target_addresses = list()
        is_discovery_success = False
        address_separator_index = TargetNodeAddress.rfind('.')
        target_prefix = TargetNodeAddress[:address_separator_index-1]
        target_sequence_num = TargetNodeAddress[address_separator_index+1:]
        for output in output_lines:
            if ("127.0.0.1:"+str(portnumber)) in output:
                log("Discovery Succeeded.")
                (iscsi_local_addr, iscsi_params) = output.split(",")
                iscsi_params = iscsi_params.strip()
                (disknum, iscsi_target_node_address) = iscsi_params.split(' ')
                if target_prefix in iscsi_target_node_address and target_sequence_num in iscsi_target_node_address and "notready" not in iscsi_target_node_address:
                    log("Target Found: "+ iscsi_target_node_address + " target num:" + disknum)
                    log("Appending the target to the list "+iscsi_target_node_address+" ...")
                    is_discovery_success = True
                    target_addresses.append(iscsi_target_node_address)
        if is_discovery_success == False:
            discovery_params = {
                "error" : err,
                "LogFolder" : LogFolder,
                "TargetNodeAddress" : TargetNodeAddress,
                "TargetPortalAddress" : TargetPortalAddress,
                "TargetPortalPortNumber" : TargetPortalPortNumber
            }
            discovery_error_prompt(discovery_params)
        connection_params = {
            "TargetNodeAddress" : target_addresses,
            "LogFolder" : LogFolder,
            "LocalPortNumber" : portnumber,
            "IsMultiTarget" : IsMultiTarget
        }
        OlderVGs = storeOlderVGs()
        connect_to_target(connection_params, OlderVGs, sameMachineRecovery)
    exitonconfirmation()


def connect_to_target(connection_params, OlderVGs, sameMachineRecovery):
    portnumber = connection_params['LocalPortNumber']
    LogFolder = connection_params['LogFolder']
    TargetNodeAddress = connection_params['TargetNodeAddress']
    IsMultiTarget = connection_params['IsMultiTarget']
    connection_status = True
    output = ""
    err = ""
    if IsMultiTarget == "1":
        for target_node_addr in TargetNodeAddress:
            p=subprocess.Popen(["iscsiadm -m node -T "+target_node_addr+" -p 127.0.0.1:"+portnumber+" --login"],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,
                                )
            output = bytes_to_str(p.stdout.read())
            err = bytes_to_str(p.stderr.read())
            log("Connect Target Output:"+output+".")
            log("Connect Target Error:"+err)
            connection_status = connection_status and (("successful." in output) or ("iscsiadm: default: 1 session requested, but 1 already present." in err or (not (output and not output.isspace()))))
    else:
        p=subprocess.Popen(["iscsiadm -m node -T "+TargetNodeAddress+" -p 127.0.0.1:"+portnumber+" --login"],
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,
                            )
        output = bytes_to_str(p.stdout.read())
        err = bytes_to_str(p.stderr.read())
        log("Connect Target Output:"+output+".")
        log("Connect Target Error:"+err)
        connection_status = (("successful." in output) or ("iscsiadm: default: 1 session requested, but 1 already present." in err or (not (output and not output.isspace()))))
    if connection_status == True:
        if "successful." in output:
            log("Connection Succeeded.")
            print("\nConnection succeeded!")
            print("\nPlease wait while we attach volumes of the recovery point to this machine...")
            log("Mounting Volumes to the Mount Paths.")
            MountILRVolumes(LogFolder, OlderVGs, sameMachineRecovery)
            log("Mounting of volumes completed successfully.")
            print("\nAfter recovery, remove the disks and close the connection to the recovery point by clicking the 'Unmount Disks' button from the portal or by using the relevant unmount command in case of powershell or CLI.")
            print("\nAfter unmounting disks, run the script with the parameter 'clean' to remove the mount paths of the recovery point from this machine.")
            connection_status = True
        elif "iscsiadm: default: 1 session requested, but 1 already present." in err or (not (output and not output.isspace())):
            log("Already connected to target.")
            print("\nThe target has already been logged in via an iSCSI session.")
            log("Mounting Volumes to the Mount Paths.")
            MountILRVolumes(LogFolder, OlderVGs, sameMachineRecovery)
            log("Mounting of volumes completed successfully.")
            print("\nAfter recovery, remove the disks and close the connection to the recovery point by clicking the 'Unmount Disks' button from the portal or by using the relevant unmount command in case of powershell or CLI.")
            print("\nAfter unmounting disks, run the script with the parameter 'clean' to remove the mount paths of the recovery point from this machine.")
            connection_status = True
        else:
            connection_status = False
    return connection_status

def generate_securetcptunnel_code(script_folder):
    SecureTCPTunnelCode ="""#!/usr/bin/python
import __future__
import threading,subprocess
import time
import asyncore
import pprint, socket, ssl
import select
import logging,sys,os
from datetime import datetime,timedelta

def bytes_to_str(byteArray):
    global encoding 
    encoding = "utf-8"
    if type(byteArray) == str:
        return byteArray
    return str(byteArray,encoding)

def isEmpty(data):
    emptystr = ''
    if type(data) is bytes:
        emptystr = b''
    return True if (data == emptystr) else False 
        
class SecureTCPTunnelServer(asyncore.dispatcher):

    def __init__(self, port_range, ILRTargetInfo, ilr_config_file):

        self.logger = logging.getLogger('SecureTCPTunnelServer')

        asyncore.dispatcher.__init__(self)
        ilrconfig = open(ilr_config_file,"a+")
        minport, maxport = port_range
        port = minport
        self.ILRTargetInfo = ILRTargetInfo
        TargetPortalAddress, TargetPortalPortNumber,TargetNodeAddress,ScriptId,VMName,LogFolder = ILRTargetInfo
        gcthread = GCThread("GCThread",TargetNodeAddress)
        gcthread.start()
        while port <= maxport:
            try:
                SocketAddress = ('localhost', port)
                self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
                self.bind(SocketAddress)
                self.address = self.socket.getsockname()
                self.listen(1)
                self.logger.info('Listening on %s', self.address)
                ilrconfig.write("\\n%s,%s,%d,%s,%d,%d,%s,%s" % (ScriptId,TargetPortalAddress,TargetPortalPortNumber,TargetNodeAddress,port,os.getpid(),VMName,LogFolder))
                ilrconfig.close()
                break
            except socket.error as ex:
                (value,message) = ex.args 
                self.logger.error("socket.error - %d, Port: %d - %s" % (value,port,message))
                if value == 98: 
                    self.close()
                    port=port+1
                else:
                    break
        return

    def handle_accept(self):

        client_info = self.accept()

        self.logger.info('Accepted client connection from %s', client_info[1])

        try:
            cthread=ClientThread("ClientThread",clientsock=client_info[0],ILRTargetInfo=self.ILRTargetInfo)
            cthread.start()
        except Exception as e:
            self.logger.warning("Exception raised while creating client thread")
            if hasattr(e, 'message'):
                self.logger.warning("Exception: "+e.message) 
            else:
                self.logger.warning("Exception: "+ str(e))
        return


    def handle_close(self):

        self.logger.info('Closing the Server.')

        self.close()

        return

class GCThread (threading.Thread):

    def __init__(self, name, targetNodeAddress):
        self.logger = logging.getLogger('GCThread')
        threading.Thread.__init__(self)
        self.name = name
        self.TargetNodeAddress = targetNodeAddress

    def run(self):
        self.logger.info("Starting " + self.name)
        self.endtime = datetime.now()+timedelta(minutes=720)
        self.logger.info("GC end Time " + str(self.endtime.strftime("%Y%m%d%H%M%S")))
        while True:
            time.sleep(60)
            self.logger.info("GC Started")
            self.logger.info("GC current Time " + str(datetime.now().strftime("%Y%m%d%H%M%S")))
            if self.endtime < datetime.now():
                self.logger.info("SecureTCPTunnel reached 12 hours active window. Killing the process.")
                try:
                    p = subprocess.Popen(["iscsiadm -m node -T "+self.TargetNodeAddress+" --logout"],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,
                                )
                    output = bytes_to_str(p.stdout.read())
                    err = bytes_to_str(p.stderr.read())
                    self.logger.info("Logout Target Output:"+output+".")
                    self.logger.info("Logout Target Error:"+err)
                    if "successful." in output:
                        self.logger.info("Logout Succeeded.")
                except Exception as e:
                    self.logger.warning("Exception raised while creating client thread")
                    if hasattr(e, 'message'):
                        self.logger.warning("Exception: "+e.message) 
                    else:
                        self.logger.warning("Exception: "+ e) 
                    #self.logger.warning("Exception: "+e.message)
                self.logger.info("GC Completed")
                os._exit(0)


class ServerThread (threading.Thread):

    def __init__(self, name, clientsock, serversock):
        self.logger = logging.getLogger('ServerThread')
        threading.Thread.__init__(self)
        self.name = name
        self.chunk_size = 131072
        self.clientsocket = clientsock
        self.serversocket = serversock

    def run(self):

        self.logger.info("Starting " + self.name)
        try:
            while True:
                self.logger.info("reading from server")
                data = self.serversocket.recv(self.chunk_size)
                if isEmpty(data) == False:
                    self.logger.info("sending to client")
                    sent=self.clientsocket.send(data[:len(data)])
                    self.logger.info("sent to client (%d)" % (sent) )
                elif isEmpty(data) == True:
                    break

        except socket.error as ex:
            (value,message) = ex.args
            self.logger.error('socket.error - ' + bytes_to_str(message))

        self.logger.info("Disconnected from Server")
        self.clientsocket.close()
        self.serversocket.close()

class ClientThread (threading.Thread):
    def __init__(self, name, clientsock, ILRTargetInfo):
        self.logger = logging.getLogger('ClientThread')
        threading.Thread.__init__(self)
        self.logger.info("Creating Client Thread for new connection")
        self.name = name
        self.chunk_size=131072
        self.clientsocket=clientsock
        TargetPortalAddress, TargetPortalPortNumber,TargetNodeAddress,ScriptId,VMName,LogFolder = ILRTargetInfo
        self.logger.info("LogFolder:"+LogFolder)
        #self.logger.info("System Version: %s" % (sys.version_info))
        if sys.version_info < (2,7,9):
            self.logger.info("sys version less then 2.7.9")
            ssocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.serversocket = ssl.wrap_socket(ssocket)

            self.serversocket.connect((TargetPortalAddress, TargetPortalPortNumber))
            #print "connection succeeded %s %s" % (TargetPortalAddress, TargetPortalPortNumber)

            #cert = self.serversocket.getpeercert()
            #print repr(self.serversocket.getpeername())
            #print pprint.pformat(self.serversocket.getpeercert())
            #print self.serversocket.cipher()
        else:
            self.logger.info("creating ssl stream")
            self.logger.info("TargetPortalAddress:" + TargetPortalAddress)
            context = ssl.create_default_context()
            context = ssl.SSLContext(ssl. PROTOCOL_TLSv1_2)
            context.verify_mode = ssl.CERT_OPTIONAL
            context.check_hostname = True
            context.load_default_certs()
            self.logger.info("checking hostname")
            hostname_tocheck = TargetPortalAddress
            if "privatelink" in TargetPortalAddress:
                self.logger.info("hostname contains privatelink")
                try:
                    hostname_tocheck = self.GetOriginalAddressFromPE(TargetPortalAddress)
                except Exception as inst:
                    self.logger.info(bytes_to_str(inst))
                self.logger.info("new hostname_tocheck:" + hostname_tocheck)
            try:
                self.logger.info("hostname_tocheck:" + hostname_tocheck)
                self.serversocket = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=hostname_tocheck)

                self.serversocket.connect((TargetPortalAddress, TargetPortalPortNumber))
                self.logger.info("connection succeeded %s %s" % (TargetPortalAddress, TargetPortalPortNumber))
                self.logger.info("Handshare in progress")
                self.serversocket.do_handshake()
                self.logger.info("Handshare done")
            except 	ssl.SSLError as err:
                if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                    select.select([self.serversocket], [], [])
                elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                    select.select([], [self.serversocket], [])
                else:
                    raise   
                cert = self.serversocket.getpeercert()

        self.logger.info("SSL Done %s %s" % (TargetPortalAddress, TargetPortalPortNumber))
        self.sthread=ServerThread("ServerThread",self.clientsocket,self.serversocket)
        self.sthread.start()

    def GetOriginalAddressFromPE(self, peaddress):
        result = []
        try:
            self.logger.info("inside GetOriginalAddressFromPE")
            address_list = peaddress.split(".")
            address_list.remove("privatelink")
            self.logger.info(address_list)
            first = address_list[0]
            address_list.remove(first)
            first_parts = first.split("-")
            result.append(first_parts[-2] + "-" + first_parts[-1])
            result.extend(address_list)
        except Exception as inst: 
            result = peaddress.split(".")
            self.logger.info(bytes_to_str(inst))
        return ".".join(result)


    def run(self):
        self.logger.info("Starting " + self.name)
        try:

            while True:
                self.logger.info("Reading from client")
                data = self.clientsocket.recv(self.chunk_size)
                if isEmpty(data) == False:
                    self.logger.info("sending to server")
                    sent=self.serversocket.send(data[:len(data)])
                    self.logger.info("sent to server (%d)" % (sent))
                elif isEmpty(data) == True:
                    break

        except socket.error as ex:
            (value,message) = ex.args
            self.logger.error('socket.error - ' + bytes_to_str(message))

        self.logger.info("Disconnected from client")

        self.clientsocket.close()
        self.serversocket.close()

def SecureTCPTunnelMain(args):
    OSVersion=sys.argv[1]
    LOG_FOLDER=sys.argv[2]
    ScriptId=sys.argv[3]
    MinPort=int(sys.argv[4])
    MaxPort=int(sys.argv[5])
    TargetPortalAddress=sys.argv[6]
    TargetPortalPortNumber=int(sys.argv[7])
    TargetNodeAddress=sys.argv[8]
    VMName=sys.argv[9]
    LOG_FILENAME = LOG_FOLDER + "/Scripts/SecureTCPTunnelLog.log"
    logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',)
    ILRTargetInfo=(TargetPortalAddress, TargetPortalPortNumber,TargetNodeAddress,ScriptId,VMName,LOG_FOLDER)
    ilr_config_file = '/etc/MicrosoftAzureBackupILR/mabilr.conf'
    port_range = (MinPort, MaxPort) # let the kernel give us a port
    server = SecureTCPTunnelServer(port_range, ILRTargetInfo, ilr_config_file)
    asyncore.loop()
if __name__ == "__main__":
    SecureTCPTunnelMain(sys.argv)
    """
    script_file_path = os.path.join(script_folder, "SecureTCPTunnel.py")
    f = open(script_file_path, "w+")
    f.write(SecureTCPTunnelCode)
    f.close()
    os.chmod(script_file_path, stat.S_IXGRP)

def get_osname_for_script(OsName):
    lowercase_osname = OsName.lower()
    if "ubuntu" in lowercase_osname:
        OsName = "Ubuntu"
    elif "debian" in lowercase_osname:
        OsName = "Debian"
    elif "centos" in lowercase_osname:
        OsName = "CentOS"
    elif "red hat" in lowercase_osname or "rhel" in lowercase_osname:
        OsName = "RHEL"
    elif "opensuse" in lowercase_osname:
        OsName = "OpenSUSE"
    elif ("suse" in lowercase_osname and "enterprise" in lowercase_osname) or "sles" in lowercase_osname or "sle_hpc" in lowercase_osname:
        OsName = "SLES"
    elif "oracle" in lowercase_osname:
        OsName = "Oracle"
    return OsName

def main(argv):
    print ("Microsoft Azure VM Backup - File Recovery")
    print ("______________________________________________")
    print ("Please verify the license, terms and conditions for using this script as mentioned here: https://aka.ms/OpenSourceLicenseForFileRecovery")
    print ("                                                                                         ------------------------------------------------")
    
    try:
        (Os, Version) = GetOsConfigFromReleasesFolder()

        if Version.count(".") > 1:
            Versions = Version.split(".")
            Version = Versions[0] + "." + Versions[1]
        OsVersion = float(Version)
        OsName = get_osname_for_script(Os)
        SupportedOSes = ["Ubuntu", "Debian", "CentOS", "RHEL", "SLES", "OpenSUSE", "Oracle"]
        OsVersionDict = {"Ubuntu" : 12.04,
                    "Debian" : 7,
                    "CentOS" : 6.5,
                    "RHEL" : 6.7,
                    "SLES" : 12,
                    "OpenSUSE" : 42.2,
                    "Oracle" : 6.4}
        OsMajorVersionDict = {"Ubuntu" : 12,
                    "Debian" : 7,
                    "CentOS" : 6,
                    "RHEL" : 6,
                    "SLES" : 12,
                    "OpenSUSE" : 42,
                    "Oracle" : 6}
        OsMinorVersionDict = {
                    "CentOS" : 5,
                    "RHEL" : 5,
                    "OpenSUSE" : 2,
                    "Oracle" : 4}
        print("Checking for OS Compatibility: DONE")
        if OsName in SupportedOSes:
            LowerVersion = OsVersionDict[OsName]
            if not is_supported(OsVersion, LowerVersion):
                isSupportedVersion = False
                if OsName in ["CentOS", "RHEL" , "OpenSUSE", "Oracle"] and Version.count(".") == 1:
                    Versions = Version.split(".")
                    OSMajorVersion = int(Versions[0])
                    OSMinorVersion = int(Versions[1])
                    LowestMajorVersion = OsMajorVersionDict[OsName]
                    LowestMinorVersion = OsMinorVersionDict[OsName]
                    if OSMajorVersion == LowestMajorVersion and OSMinorVersion >= LowestMinorVersion:
                        isSupportedVersion = True
                if isSupportedVersion == False:
                    supported_os_msg()
                    ans=input_for_python_Version("Please press 'Y' if you still want to continue with running the script, 'N' to abort the operation. : ")
                    if ans not in ['y','Y']:
                        exit()
        else:
            print ("You are running the script from an unsupported OS Version")
            supported_os_msg()
            ans=input_for_python_Version("Please press 'Y' if you still want to continue with running the script, 'N' to abort the operation. : ")
            if ans not in ['y','Y']:
                exit()
    except:
        print ("OsName not recognized if your os is in the list 'Ubuntu', 'Debian', 'CentOS', 'RHEL', 'SLES', 'OpenSUSE', 'Oracle'.\n Please enter OsName as they appear in the list")
        response = input_for_python_Version("Enter you os name: ")
        OsName = get_osname_for_script(response.strip())
        response = input_for_python_Version("Enter the os version: ")
        Version = response.strip()
        if OsName not in ["Ubuntu", "Debian", "CentOS", "RHEL", "SLES", "OpenSUSE", "Oracle"]:
            print(("Your Os " + OsName + " is not yet supported"))
            supported_os_msg()
            exit()
    
    # initialize the parameters required for ILR script to run
    MinPort=5365
    MaxPort=5396
    # set up script directory and set up the logs directory
    # volume will be mounted in this directory only
    #os.getcwd - gives the current working directory 
    script_directory = os.getcwd()
    new_guid = str(time.strftime("%Y%m%d%H%M%S"))
    #logfolder is cwd/machineName-newGuid
    log_folder = script_directory + "/" + MachineName + "-" + new_guid
    #scriptfolder is logfolder/scripts
    script_folder = log_folder + "/Scripts"
    os.mkdir(log_folder)
    os.mkdir(script_folder)
    logfilename = script_folder + "/MicrosoftAzureBackupILRLogFile.log"
    global logfile
    logfile = open(logfilename,'a+')
    MABILRConfigFolder="/etc/MicrosoftAzureBackupILR"
    install_prereq_packages(OsName)
    if not os.path.exists(MABILRConfigFolder):
        os.mkdir(MABILRConfigFolder)

    hostname = socket.gethostname()
    vmname = VMName.split(';')
    try:
        if (hostname.lower() == vmname[2].lower() or hostname.lower() == MachineName.lower()):
            print("Checking if this script can be run on this machine...")
            try:
                print("Checking for large disks on the backed up VM: DONE")
                if IsLargeDisk == "1":
                    print("Backed-up machine has large number of disks (>16) or large disks (> 4 TB each). It's not recommended to execute the script on the same machine for restore, since it will have a significant impact on the VM.")
                    ans=input_for_python_Version("Please press 'N' to abort the operation. Press 'Y' if you want to continue with running the script : ")
                    if ans not in ['y','Y']:
                        exit()
            except Exception as e:
                log("Exception raised while checking for large disks.")
                log("Exception: " + e.message)
            try:
                CheckForRAIDDisks(log_folder)
                log("isStorageSpaceExists"+str(isStorageSpaceExists))
                print("Checking whether LVM exists on this machine: DONE")
                if isStorageSpaceExists == True :
                    print("\nMount the recovery point only if you are SURE THAT THESE ARE NOT BACKED UP/ PRESENT IN THE RECOVERY POINT.")
                    print("If they are already present, it might corrupt the data irrevocably on this machine.")
                    print("It is recommended to run this script on any other machine with similar OS to recovery files.")
                    ans=input_for_python_Version("\nShould the recovery point be mounted on this machine? ('Y'/'N') ")
                    if 'y' in ans or 'Y' in ans:
                        log("user selected to continue")
                    else:
                        print("\nPlease run this script on any other machine with similar OS to recover files.")
                        exitonconfirmation()
            except Exception as e:
                log("Exception raised while checking for LVMs.")
                log("Exception: " + e.message)
        else:
            print("Checking for large disks: DONE")
            print("Checking for LVMs: DONE")

        try:
            proc = subprocess.Popen(["curl "+TargetPortalAddress+":"+str(TargetPortalPortNumber)+" --connect-timeout 2"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output = proc.stdout.read()
            output = bytes_to_str(output)
            error = proc.stderr.read()
            error = bytes_to_str(error)
            log("Output: " + output)
            output = output.lower()
            error = error.lower()
            print("Checking for network connectivity: DONE")
            if ("timed out" in output) or ("timed out" in error):
                print("Your system doesn't have access to '" + TargetPortalAddress + "' on port " + TargetPortalPortNumber + " (outbound). ILR Script won't be able to run successfully.\n")   
                print("Please add rules in the NSG to allow '" + TargetPortalAddress + "' on port " + TargetPortalPortNumber + " (outbound), and also allow Public DNS resolution on port 53 (outbound).")
                ans=input_for_python_Version("Please press 'N' to abort the operation. Press 'Y' if you still want to continue with running the script : ")
                if ans not in ['y','Y']:
                    exit()
        except Exception as e:
            log("Exception raised while checking for network connectivity.")
            log("Exception: " + e.message)

        try:
            proc = subprocess.Popen(["/usr/bin/openssl ciphers -v | grep ECDHE-RSA-AES256-GCM-SHA384"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output = proc.stdout.read()
            output = bytes_to_str(output).strip()
            error = proc.stderr.read()
            error = bytes_to_str(error)
            log ("Output: " + output)
            log ("Error: " + error)
            if error:
                log("Error while checking the required cipher suite: " + error + "\n")
            else:
                print("Checking for required cipher suite: DONE")
            if output:
                log("Required cipher suite is there.")
            else:
                log("Required cipher suite is not there.")
                print("Required cipher suite is not there. ILR Script won't be able to run successfully.\n")
                ans=input_for_python_Version("Please press 'N' to abort the operation. Press 'Y' if you want to continue with running the script : ")
                if ans not in ['y','Y']:
                    exit()
        except Exception as e:
            log("Exception raised while checking for cipher suites.")
            log("Exception: " + e.message)

        try:
            proc = subprocess.Popen(["curl --max-time 10 ifconfig.io"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output = proc.stdout.read()
            output = bytes_to_str(output)
            error = proc.stderr.read()
            error = bytes_to_str(error)
            if output:
                log("\nPublic IP: " + output)
            else:
                log("Error while fetching public IP: " + error + "\n")
        except Exception as e:
            log("Exception raised while fetching the public IP of the machine.")
            log("Exception: " + e.message)
    except:
        log("Error occured while checking pre-requisites.")

    log("Generating SecureTCPTunnel code")
    generate_securetcptunnel_code(script_folder)

    log("Setting ACL to Log and script Folder")
    isSetfaclInstalled = is_package_installated("setfacl")
    if isSetfaclInstalled:
        shell_cmd = 'setfacl --set="user::rwx,group::rwx,other::---" ' + log_folder
        run_shell_cmd(shell_cmd)
        shell_cmd = 'setfacl --default --set="user::rwx,group::rwx,other::---" ' + log_folder
        run_shell_cmd(shell_cmd)
        shell_cmd = 'setfacl --set="user::rwx,group::rwx,other::---" ' + script_folder
        run_shell_cmd(shell_cmd)
        shell_cmd = 'setfacl --default --set="user::rwx,group::rwx,other::---" ' + script_folder
        run_shell_cmd(shell_cmd)
    else:
        shell_cmd = 'chmod -R "ug+rwx" ' + log_folder
        run_shell_cmd(shell_cmd)
        shell_cmd = 'chmod -R "ug+rwx" ' + script_folder
        run_shell_cmd(shell_cmd)
    log("Setting ACL succeeded")
    check_for_open_SSL_TLS_v12()
    DoCleanUp = len(argv) > 0 and "clean" in argv
    ilr_params = {
        "MinPort": MinPort,
        "MaxPort": MaxPort,
        "VMName" : VMName,
        "OsNameVersion" : OsName + ";" + Version + ";",
        "MachineName" : MachineName,
        "TargetPortalAddress": TargetPortalAddress,
        "TargetPortalPortNumber": int(TargetPortalPortNumber),
        "TargetNodeAddress": TargetNodeAddress,
        "TargetUserName": TargetUserName,
        "TargetPassword": TargetPassword,
        "InitiatorChapPassword": InitiatorChapPassword,
        "ScriptId": ScriptId,
        "LogFolder": log_folder,
        "SciptFolder": script_folder,
        "DoCleanUp" : DoCleanUp,
        "IsMultiTarget" : IsMultiTarget,
        "IsPEEnabled" : IsPEEnabled, 
        "IsLargeDisk" : IsLargeDisk
    }

    ILRMain(ilr_params)
 
if __name__ == "__main__":
    if os.getuid() != 0:
        print ("Launching the ilrscript as admin")
        python_script_with_args = " ".join(sys.argv)
        pythonVersion = get_python_version()
        os.system("sudo " + pythonVersion+ " " + python_script_with_args)
        exit(0)
    else:
        global VMName,MachineName,TargetPortalAddress,TargetPortalPortNumber,TargetNodeAddress,InitiatorChapPassword,ScriptId,TargetUserName,TargetPassword, IsMultiTarget
        VMName="iaasvmcontainerv2;ompv_serversv2_rg;OMPV-APPV2-STG"
        MachineName="OMPV-APPV2-STG"
        TargetPortalAddress="pod01-rec2.uan.backup.windowsazure.com"
        TargetPortalPortNumber="3260"
        TargetNodeAddress="iqn.2016-01.microsoft.azure.backup:4338435508451104153-3062737-2703039386320677198-2702775348000916232.639122617688980634"
        InitiatorChapPassword="76a4dced41ff78"
        ScriptId="0bb39d5d-d742-4106-b3a9-6945bede0120"
        TargetUserName="4338435508451104153-d9034fab-c563-45d4-9789-6a79f5a70e57"
        TargetPassword="UserInput012345"
        IsMultiTarget = "1"
        IsPEEnabled = "0"
        IsLargeDisk = "False"
        main(sys.argv[1:])