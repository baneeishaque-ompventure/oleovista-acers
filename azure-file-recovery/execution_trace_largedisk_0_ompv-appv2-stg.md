# Execution Trace: `largedisk_0_OMPV-APPV2-STG_1_uan_...py`

**File:** `/Users/dk/lab-data/oleovista-acers/largedisk_0_OMPV-APPV2-STG_1_uan_4338435508451104153_122617688980_d9034fabc56345d497896a79f5a70e5776a4dced41ff78.py`

**Purpose:** Microsoft Azure VM Backup — File Recovery (ILR) script for large disks. Establishes iSCSI connection via a local SSL tunnel, mounts recovery point volumes, and provides LVM/RAID handling.

---

## **Phase 1: Entry Point & Privilege Escalation**

```python
if __name__ == "__main__":
    if os.getuid() != 0:
        print ("Launching the ilrscript as admin")
        python_script_with_args = " ".join(sys.argv)
        pythonVersion = get_python_version()
        os.system("sudo " + pythonVersion+ " " + python_script_with_args)
        exit(0)
```

- Script checks UID; if not root, re-launches itself via `sudo` with same arguments and exits.
- If already root, proceeds with hard-coded recovery parameters:

```python
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
```

- Calls `main(sys.argv[1:])`.

---

## **Phase 2: `main()` — Pre-flight, OS Check & Setup**

### Step 1: License Header
Prints open-source license notice with URL.

### Step 2: OS Detection — `GetOsConfigFromReleasesFolder()`
```python
proc = subprocess.Popen("egrep '^(VERSION_ID)=' /etc/*-release", ...)
proc = subprocess.Popen("egrep '^(NAME)=' /etc/*-release", ...)
```
- Extracts `VERSION_ID` and `NAME` from `/etc/*-release` files.
- Fallback: `egrep 'release' /etc/*-release` and parses with string indexing.
- Returns `(osname, osversion)`.
- Normalizes distro name via `get_osname_for_script()` into one of: `Ubuntu`, `Debian`, `CentOS`, `RHEL`, `SLES`, `OpenSUSE`, `Oracle`.

### Step 3: OS Version Compatibility
```python
OsVersion = float(Version)   # e.g. "12.04" → 12.04
OsVersionDict = {"Ubuntu": 12.04, "Debian": 7, "CentOS": 6.5, ...}
```
- If `OsVersion < LowerVersion`:
  - For RHEL-family (CentOS/RHEL/OpenSUSE/Oracle) with single dot version, checks major/minor separately to allow minor >= required.
  - Otherwise prints `supported_os_msg()` and prompts to continue/abort.

### Step 4: Directory Structure
```python
script_directory = os.getcwd()
new_guid = str(time.strftime("%Y%m%d%H%M%S"))
log_folder = script_directory + "/" + MachineName + "-" + new_guid
script_folder = log_folder + "/Scripts"
os.mkdir(log_folder)
os.mkdir(script_folder)
```
Example: `<cwd>/OMPV-APPV2-STG-20260422170746/Scripts/`

### Step 5: Log Initialization
```python
logfilename = script_folder + "/MicrosoftAzureBackupILRLogFile.log"
logfile = open(logfilename,'a+')
```
- Global `logfile` used by `log()` helper throughout.

### Step 6: Prerequisite Packages — `install_prereq_packages(OsName)`
- Packages: `setfacl`, `iscsiadm`, `lshw`
- Checks presence with `which`.
- If any missing:
  - Prints list (maps `iscsiadm` → `open-iscsi` or `iscsi-initiator-utils` per distro).
  - Prompts: `"Do you want us to install ...?"`
  - On `Y`: calls `install_packages()` which loops through each:
    - Builds installer command: `apt-get --assume-yes install`, `yum -y install`, or `zypper install`.
    - Runs command, waits, then verifies with `which`.
    - Logs stdout/stderr; on error prints details and calls `exitonconfirmation()`.

### Step 7: Config Directory
```python
MABILRConfigFolder="/etc/MicrosoftAzureBackupILR"
if not os.path.exists(MABILRConfigFolder):
    os.mkdir(MABILRConfigFolder)
```

### Step 8: Same-Machine Recovery Guard
```python
hostname = socket.gethostname()
vmname = VMName.split(';')
if (hostname.lower() == vmname[2].lower() or hostname.lower() == MachineName.lower()):
    sameMachineRecovery = True
```
- If hostname matches backed-up VM name or provided machine name:

#### Large Disk Warning (`IsLargeDisk == "1"`):
```
Backed-up machine has large number of disks (>16) or large disks (> 4 TB each).
It's not recommended to execute the script on the same machine...
```
- Prompts to continue or abort.

#### RAID/LVM Check — `CheckForRAIDDisks(log_folder)`
- Runs `lshw -xml -class disk -class volume` → writes to `<log_folder>/Scripts/lshw2.xml`.
- Parses XML tree:
  - For each `disk` node:
    - Checks `vendor == 'MABILR I'` (Azure ILR disk marker).
    - Collects volumes:
      - `description == "Linux raid autodetect partition"` → RAID entry.
      - `"LVM" in description` → LVM entry.
      - Otherwise regular volume.
- If any RAID/LVM found, prints warning:
  ```
  Mount the recovery point only if you are SURE THAT THESE ARE NOT BACKED UP/ PRESENT IN THE RECOVERY POINT.
  If they are already present, it might corrupt the data irrevocably on this machine.
  It is recommended to run this script on any other machine with similar OS to recover files.
  ```
- Prompts `Y/N`; aborts if `N`.

### Step 9: Network Connectivity Check
```python
proc = subprocess.Popen(["curl "+TargetPortalAddress+":"+str(TargetPortalPortNumber)+" --connect-timeout 2"], ...)
```
- If `"timed out"` in output or error:
  - Prints NSG and DNS resolution guidance.
  - Prompts to continue/abort.

### Step 10: Cipher Suite Check
```python
proc = subprocess.Popen(["/usr/bin/openssl ciphers -v | grep ECDHE-RSA-AES256-GCM-SHA384"], ...)
```
- Verifies required cipher suite exists; if not, prompts to continue/abort.

### Step 11: Public IP Fetch (informational)
```python
proc = subprocess.Popen(["curl --max-time 10 ifconfig.io"], ...)
```
- Logs public IP to file only; no user impact.

### Step 12: Generate `SecureTCPTunnel.py`
Calls `generate_securetcptunnel_code(script_folder)` — writes the embedded SSL tunnel code (see **Phase 7** below) to `<script_folder>/SecureTCPTunnel.py` and sets executable bit (`stat.S_IXGRP`).

### Step 13: Set Folder ACLs
```python
if isSetfaclInstalled:
    setfacl --set="user::rwx,group::rwx,other::---" <log_folder>
    setfacl --default --set="user::rwx,group::rwx,other::---" <log_folder>
    ... same for <script_folder>
else:
    chmod -R "ug+rwx" <log_folder> <script_folder>
```
- Restricts access to owner/group only.

### Step 14: TLSv1.2 Check — `check_for_open_SSL_TLS_v12()`
```python
p = subprocess.Popen("openssl ciphers -v | awk '{print $2}' | sort | uniq", ...)
```
- Verifies `"TLSv1.2"` appears in cipher list; aborts if missing.

### Step 15: Cleanup Flag
```python
DoCleanUp = len(argv) > 0 and "clean" in argv
```

### Step 16: Build `ilr_params` Dictionary
Collects all parameters (ports, addresses, credentials, paths, flags) and calls `ILRMain(ilr_params)`.

---

## **Phase 3: `ILRMain()` — Session Detection & Tunnel Launch**

### Step 17: Log Parameters
Writes all incoming values to `MicrosoftAzureBackupILRLogFile.log`.

### Step 18: Password Prompt
```python
if TargetPassword == "UserInput012345" and not docleanup:
    TargetPassword = input("Please enter the password as shown on the portal...")
    if len(TargetPassword) != 15:
        print("You need to enter the complete 15 character password...")
        exitonconfirmation()
```

### Step 19: Existing Session Detection
```python
proc = subprocess.Popen(["tail","-n","1","/etc/MicrosoftAzureBackupILR/mabilr.conf"], ...)
```
- **`mabilr.conf` format**: `<ScriptId>,<TargetPortal>,<TargetPort>,<TargetNode>,<LocalPort>,<PID>,<VMName>,<LogFolder>`
- If record exists:
  - Runs `iscsiadm -m session` to check if target already connected.
  - If target address matches current `TargetNodeAddress`:
    - If `docleanup`: auto-confirms `Y`.
    - Else: prints *"We detected a session already connected to the recovery point of the VM '<lastvmname>'"* and prompts to unmount.
    - On `Y`: calls `UnMountILRVolumes(lastlogfolder)` then logs out iSCSI targets via `logout_targets(target_address_prefix)`.
    - On `N`: aborts.

#### `UnMountILRVolumes(LogFolder)` (line 340)
- `mount | grep '<LogFolder>'` → split each line, `umount '<device>'` for each mount.
- Reads `<LogFolder>/Scripts/Activated_VG.txt`, runs `vgchange -a n <VGs>` to deactivate volume groups.
- Truncates activated VG file.
- Logs all stdout/stderr.

### Step 20: Same-Machine Recovery Configuration
If hostname matches:
- Calls `UpdateISCSIConfig(LogFolder, TargetUserName, TargetPassword)`:

#### `UpdateISCSIConfig()` (line 803)
1. Creates temp file with patterns to remove (blanked auth lines).
2. `grep -v -f <temp1> /etc/iscsi/iscsid.conf > <temp2>` → filters out old credentials.
3. Appends new CHAP config:
   ```
   discovery.sendtargets.auth.authmethod = CHAP
   discovery.sendtargets.auth.username = <OsName><TargetUserName>
   discovery.sendtargets.auth.password = <TargetPassword>
   node.session.auth.authmethod = CHAP
   node.session.auth.username = <OsName><TargetUserName>
   node.session.auth.password = <TargetPassword>
   ```
4. Copies temp2 over original `/etc/iscsi/iscsid.conf`.

### Step 21: Kill Stale `SecureTCPTunnel`
If previous `mabilr.conf` record has a PID:
```python
proc = subprocess.Popen(["ps","-ww","-o","args","-p",processid], ...)
```
- If process command line contains `"SecureTCPTunnel"`:
  - `kill -9 <pid>` to free port (especially 3260 on RHEL-family).

### Step 22: Cleanup-Only Exit
If `docleanup == True`:
```
The local mount paths have been removed.
Please make sure to click the 'Unmount disks' from the portal...
```
Calls `exitonconfirmation()` and exits.

### Step 23: Launch `SecureTCPTunnel` (if not cleanup)
```python
if not install_prereq_packages_for_securetcptunnel(): ...
```
- Checks `import asyncore`; if `ImportError` (Python ≥3.12), offers to install `pyasyncore`.
  - Uses system package manager: `python3-pyasyncore` or `python-pyasyncore`.
  - Verifies import after install; aborts on failure.
- For RHEL-family: forces `MinPort=MaxPort=3260`.
- Builds command:
  ```python
  [pythonVersion,
   LogFolder + "/Scripts/SecureTCPTunnel.py",
   OSName, LogFolder, ScriptId,
   str(MinPort), str(MaxPort),
   TargetPortalAddress, str(TargetPortalPortNumber),
   TargetNodeAddress, VMName]
  ```
- `subprocess.Popen()` starts tunnel; logs PID.
- **Poll for config record**:
  - Reads `/etc/MicrosoftAzureBackupILR/mabilr.conf` looking for line with matching `ScriptId` and `PID`.
  - Retries up to 2 times, 1s interval.
  - If not found → prints port-blocked error, suggests checking port usage, exits.

### Step 24: iSCSI Discovery
```python
p = subprocess.Popen(["iscsiadm -m discovery -t sendtargets -p 127.0.0.1:"+portnumber], ...)
```

#### Single-Target (`IsMultiTarget == "0"`)
- Checks output for `"blocked"` → Private Endpoint error; exits with vnet instruction.
- Checks for `"notready"` (large disk not ready):
  - Retries up to 4 times, 5-minute wait between attempts.
  - If still `notready` → exits with *"Please retry after 10 mins."*
- Verifies line format:
  ```
  127.0.0.1:<port>,-1 <TargetNodeAddress>
  ```
- On success: `OlderVGs = storeOlderVGs()` → runs `vgs -o +vguuid`, extracts VG UUIDs.
- Calls `connect_to_target(connection_params, OlderVGs, sameMachineRecovery)`.

#### Multi-Target (`IsMultiTarget == "1"`)
- Parses all discovery output lines.
- Filters lines containing `127.0.0.1:<port>`.
- Extracts target address after comma; matches target prefix and sequence number from `TargetNodeAddress`.
- Builds list `target_addresses`.
- Calls `connect_to_target()` with list.

---

## **Phase 4: `connect_to_target()` — iSCSI Login**

### Step 25: Login
```python
p = subprocess.Popen(["iscsiadm -m node -T "+target+" -p 127.0.0.1:"+portnumber+" --login"], ...)
```
- For single target: logs in once.
- For multi-target: iterates list.
- **Success criteria**:
  - `"successful." in output` OR
  - `"iscsiadm: default: 1 session requested, but 1 already present." in err` OR
  - Empty output (edge case).

### Step 26: Post-Login
- On success:
  - Prints *"Connection succeeded!"*
  - Calls `MountILRVolumes(LogFolder, OlderVGs, sameMachineRecovery)`.
  - Prints post-recovery instructions:
    ```
    After recovery, remove the disks and close the connection...
    run the script with the parameter 'clean' to remove the mount paths...
    ```
- On failure:
  - Builds `discovery_params` dict with `error`, paths, addresses.
  - Calls `discovery_error_prompt(params)`:
    - `"initiator failed authorization"` → wrong password.
    - `"iscsid is not running"` → service down.
    - Else → generic proxy/firewall guidance, suggests `curl` test command.

---

## **Phase 5: `MountILRVolumes()` — Disk Enumeration & Mount**

### Step 27: Hardware Scan
```python
proc = subprocess.Popen(['lshw -xml -class disk -class volume'], ...)
```
- Writes to `<LogFolder>/Scripts/lshw1.xml`.
- Parses XML similarly to `CheckForRAIDDisks()` but with `isMABILRDisk` guard.

### Step 28: Volume Classification
For each disk node (`id` contains `"disk"`):
- Tracks `vendorname`; sets `isMABILRDisk = (vendorname == "MABILR I")`.
- If `isMABILRDisk`:
  - For each child `volume`:
    - `description == "Linux raid autodetect partition"` → add tuple to `raidvolumeslist`.
    - `"LVM" in description` → append logical name to `LVMlist`, tuple to `LVlist`.
    - Else → **regular partition mount attempt**:
      1. Create mount dir: `<LogFolder>/Volume<N>`.
      2. `mount <logicalname> <mountpath>`.
      3. On error, retry `mount -o nouuid <logicalname> <mountpath>`.
      4. Persistent failure → add to `failedvolumeslist`.
  - If disk has **no volumes** but is MABILR:
    - If XML contains `"lvm"`/`"LVM"` → RAID/LVM entry.
    - Else → runs `lsblk -f <disklogicalname>` to detect filesystem.
      - If valid FS, prompts user:
        ```
        Identified the below disk which does not have volumes.
        <disklogicalname>
        Please press 'Y' to continue with mounting this disk without volume, 'N' to abort...
        ```
      - On `Y`: creates `<LogFolder>/Disk<N>`, tries mount (normal + `nouuid` retry).
      - Failure → adds to `failedvolumeslist`.

### Step 29: LVM Automation
```python
if (hasLVM or len(LVMlist) > 0) and (not sameMachineRecovery):
    ans = input("Do you want us to mount LVMs as well? ('Y'/'N') ")
```
- If `Y`: calls `LVMautomation(LogFolder, OlderVGs)`.

#### `LVMautomation()` (line 409)
1. `vgs -o +vguuid` → parse columns; index `[7]` is VG UUID.
2. `ToRenameVGs` = VGs whose UUID not in `OlderVGs` (new VGs created by Azure).
3. For each new VG:
   ```python
   renamed = VG + "_" + time.strftime("%Y%m%d%H%M%S")
   vgrename <uuid> <renamed>
   ```
   - Tracks renamed VGs (`RenamedVGs`) and failures (`NotRenamedVGs`).
4. Activate renamed VGs: `vgchange -a y <RenamedVGs>`.
5. Save all VG names (renamed + not-renamed) to `<LogFolder>/Scripts/Activated_VG.txt`.
6. For each renamed VG: `lvdisplay <vg> | grep -i Path` → extract LV device paths.
   - For each LV:
     - Create `<LogFolder>/LVM<N>`.
     - `lsblk -f <lv>` → expects 2 lines; second line contains filesystem column.
     - If FS detected: `mount <lv> <mountpath>` → `MountedLVMlist`.
     - Else: `NotMountedLVMlist`.
7. For `NotRenamedVGs`: enumerate LVs but do **not** mount (to avoid conflicts).
8. Returns `(MountedLVMlist, NotMountedLVMlist)`.
9. On exception: logs `e.message`, returns empty lists.

- If `N` or LVM automation not chosen: prints manual commands:
  ```
  $ pvs <volume name>
  $ lvdisplay <volume-group-name>
  $ mount <LV path> </mountpath>
  ```

### Step 30: Output Summary Tables
Prints sections with numbered entries:

| Table | Content | Source |
|-------|---------|--------|
| Volumes (regular) | `Disk \| Volume \| MountPath` | `volumeslist` |
| LVMs (mounted) | `LV Path \| MountPath` | `MountedLVMlist` |
| Logical Volumes | `Disk \| Volume \| Partition Type` | `LVlist` (same-machine only) |
| RAID Arrays | `Disk \| Volume \| Partition Type` | `raidvolumeslist` + `mdadm` instructions |
| Unknown FS (failed) | `Disk \| Volume \| Partition Type` | `failedvolumeslist` |
| LVM failures | LVM names | `NotMountedLVMlist` |

If any failures: directs user to log file: `<LogFolder>/Scripts/MicrosoftAzureBackupILRLogFile.log`.

Final message: *"Open File Explorer to browse for files."*

---

## **Phase 6: Cleanup Path**

If script invoked with `clean` argument:
- Skips tunnel, discovery, mount.
- Calls `UnMountILRVolumes()` on the last recorded session's log folder (from `mabilr.conf`).
- Prints:
  ```
  The local mount paths have been removed.
  Please make sure to click the 'Unmount disks' from the portal to remove the connection to the recovery point.
  ```
- Calls `exitonconfirmation()`.

---

## **Phase 7: `SecureTCPTunnel` Subprocess (Generated Code)**

**Launched as:** `<python> <LogFolder>/Scripts/SecureTCPTunnel.py <args>`

### Entry: `SecureTCPTunnelMain(args)`
- Parses CLI args (indices 1–9).
- Sets up logging to `<LOG_FOLDER>/Scripts/SecureTCPTunnelLog.log`.
- Creates `ILRTargetInfo` tuple.
- Config file: `/etc/MicrosoftAzureBackupILR/mabilr.conf`.
- Instantiates `SecureTCPTunnelServer(port_range, ILRTargetInfo, ilr_config_file)`.
- Calls `asyncore.loop()`.

### `SecureTCPTunnelServer.__init__()` (lines 1327–1358)
- Opens `mabilr.conf` in append mode.
- Iterates ports from `MinPort` → `MaxPort`:
  - `self.create_socket(AF_INET, SOCK_STREAM)`
  - `self.bind(('localhost', port))`
  - `self.listen(1)`
  - On success: writes config line:
    ```
    <ScriptId>,<TargetPortalAddress>,<TargetPort>,<TargetNodeAddress>,<port>,<pid>,<VMName>,<LogFolder>
    ```
  - Closes file, breaks.
  - On `socket.error` with `errno == 98` (EADDRINUSE): `port += 1` and retry.
  - Other errors: abort binding.

### `handle_accept()`
- When client connects (ILR script acting as client):
  - Spawns `ClientThread(clientsock, ILRTargetInfo)`.

### `ClientThread.__init__()` — SSL Upstream Connection (lines 1458–1517)
- Establishes SSL/TLS connection to Azure backup vault:
  - **Python < 2.7.9**: `ssl.wrap_socket()` (no SNI/verification).
  - **Python ≥ 2.7.9**:
    ```python
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.verify_mode = ssl.CERT_OPTIONAL
    context.check_hostname = True
    ```
    - If `TargetPortalAddress` contains `"privatelink"`, calls `GetOriginalAddressFromPE()` to derive original hostname for `server_hostname` verification.
    - `context.wrap_socket(socket.socket(...), server_hostname=hostname_tocheck)`
    - `connect((TargetPortalAddress, TargetPortalPortNumber))`
    - `do_handshake()`
- Starts `ServerThread` to pump data from server → client.

### `ServerThread.run()` (lines 1435–1455)
- Loop: `self.serversocket.recv(131072)` → `self.clientsocket.send(data)`.
- Closes sockets on empty/error.

### `ClientThread.run()` (lines 1537–1558)
- Loop: `self.clientsocket.recv(131072)` → `self.serversocket.send(data)`.
- Closes sockets on empty/error.

**Bi-directional data flow:**
```
ILR Script Client ↔ SecureTCPTunnel ClientThread ↔ SecureTCPTunnel ServerThread ↔ Azure Backup Vault (SSL)
```

### `GCThread.run()` (lines 1394–1422)
- Starts as daemon thread at tunnel launch.
- `endtime = now + 720 minutes` (12-hour window).
- Sleeps 60s intervals; when `datetime.now() >= endtime`:
  1. Logs timeout.
  2. `iscsiadm -m node -T <TargetNodeAddress> --logout`
  3. `os._exit(0)` — hard termination of tunnel process.

---

## **Key Configuration Files**

| File | Purpose |
|------|---------|
| `/etc/MicrosoftAzureBackupILR/mabilr.conf` | Tracks active tunnel: `ScriptId,Portal,Port,TargetNode,LocalPort,PID,VMName,LogFolder` |
| `/etc/iscsi/iscsid.conf` | iSCSI daemon config — updated with CHAP credentials |
| `<LogFolder>/Scripts/MicrosoftAzureBackupILRLogFile.log` | Primary ILR script log |
| `<LogFolder>/Scripts/SecureTCPTunnelLog.log` | Tunnel subprocess log |
| `<LogFolder>/Scripts/lshw1.xml` | Pre-mount hardware scan |
| `<LogFolder>/Scripts/lshw2.xml` | Pre-RAID-check scan |
| `<LogFolder>/Scripts/Activated_VG.txt` | Space-separated list of VGs activated during LVM automation |
| `<LogFolder>/Volume*` | Mount points for regular partitions |
| `<LogFolder>/Disk*` | Mount points for disks without volume labels |
| `<LogFolder>/LVM*` | Mount points for logical volumes |

---

## **Control Flow Diagram (High-Level)**

```
main()
 ├─ OS detect + version check
 ├─ mkdir <Machine>-<timestamp>/Scripts/
 ├─ install setfacl/iscsiadm/lshw (prompt if missing)
 ├─ same-machine guard (large disk + RAID/LVM warnings)
 ├─ network (curl) + cipher (openssl) checks
 ├─ generate SecureTCPTunnel.py
 ├─ set ACLs
 ├─ TLSv1.2 check
 ├─ UpdateISCSIConfig() → /etc/iscsi/iscsid.conf
 ├─ kill stale SecureTCPTunnel (via mabilr.conf + ps)
 ├─ spawn SecureTCPTunnel process
 │    └─ writes its record to /etc/MicrosoftAzureBackupILR/mabilr.conf
 ├─ wait for tunnel record (poll up to 2×)
 ├─ iscsiadm discovery (retry "notready" ×4)
 ├─ iscsiadm login
 └─ MountILRVolumes()
      ├─ lshw -xml → MABILR disk filter
      ├─ mount regular partitions (retry nouuid)
      ├─ optional: LVMautomation()
      │    ├─ vgs → rename new VGs (<name>_<timestamp>)
      │    ├─ vgchange -a y
      │    ├─ lvdisplay → mount each LV under /LVM<N>
      │    └─ save Activated_VG.txt
      └─ print summary tables (volumes, RAID, LVM, failures)
```

**Tunnel process (parallel):**
```
SecureTCPTunnel
 ├─ bind localhost:<port> (from mabilr.conf)
 ├─ ClientThread (per client):
 │    ├─ SSL connect to <TargetPortalAddress>:<TargetPortalPortNumber>
 │    ├─ ServerThread ←→ upstream (read/write loops)
 │    └─ ClientThread ↔ client (read/write loops)
 └─ GCThread: 12h timeout → iscsiadm logout → os._exit(0)
```

---

## **Error Paths & User Prompts**

| Condition | Prompt / Action |
|-----------|-----------------|
| Unsupported OS | Prints supported list, asks to continue |
| Missing packages | Asks to install; aborts if declined or fails |
| Same-machine with RAID/LVM | Strong warning; asks confirmation |
| Network timeout (curl) | NSG guidance, asks to continue |
| Cipher suite missing | Warns ILR may fail, asks to continue |
| `TargetPassword == "UserInput012345"` | Prompts for 15-char password |
| Existing iSCSI session to different VM | Prompts to unmount previous |
| Stale `SecureTCPTunnel` PID exists | Kills it automatically |
| Tunnel cannot bind port | Prints port-blocked error, exits |
| Discovery `"blocked"` (Private Endpoint) | `"run from a machine in vnet"` + exit |
| Discovery `"notready"` (large disk) | Waits 5min ×4, then exits if still not ready |
| Login failure (auth) | `discovery_error_prompt`: wrong password |
| `iscsid` not running | Prompt to start service |
| Mount failure (regular) | Retries with `nouuid`; adds to failed list |
| Disk without volume (MABILR) | Prompts to mount anyway |
| LVM present & not same-machine | Prompts to automate LVM mount |
| Any exception in `LVMautomation()` | Logs, returns empty mount lists |

---

## **Security Notes**

- **Root required**: script re-launches via `sudo` if not run as root.
- **CHAP authentication**: username = `<OsName><TargetUserName>`; password from portal entry (15 chars).
- **SSL/TLS**: `SecureTCPTunnel` uses TLSv1.2, hostname verification (with Private Link hostname reconstruction).
- **ACLs**: `setfacl` or `chmod` restricts log/script directories to owner/group.
- **12-hour timeout**: GC thread forcibly logs out and terminates tunnel after 720 minutes.
- **Port binding**: tunnel binds only to `localhost`; iSCSI connects via loopback.

---

## **Recovery Workflow (User Perspective)**

1. **Download** `largedisk_0_*.py` from Azure portal.
2. **Copy** to target Linux machine (similar OS to backed-up VM).
3. **Run** `python largedisk_0_*.py` (script auto-sudo to root).
4. **Enter password** (15-char from portal) if prompted.
5. **Confirm** warnings (large disk, RAID/LVM if same machine).
6. **Wait** for tunnel startup, iSCSI discovery, login.
7. **Volumes auto-mounted** under `<cwd>/<Machine>-<timestamp>/`.
8. **Browse files** via mounted paths (Volume*, Disk*, LVM*).
9. **After recovery**:
   - Unmount disks from portal **or** re-run script with `clean` argument.
   - Script removes local mount points.

---

**Generated:** 2026-04-22  
**Skill Used:** Code Explanation (deep-dive, pedagogical standard)
