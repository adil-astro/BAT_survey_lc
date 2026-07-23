import os
import sys
from datetime import datetime
import time
import subprocess

from makeconfig import Make_User_Config, Make_Config, Validate_User_Config
from datavalidation import Valid_Obsids
from reduction import Rebin_Lightcurve, Generate_Tasks
from constants import GLOBAL_EMIN, GLOBAL_EMAX
from executor import Run_Command, Verify_Output, NoGTIError
from utils import Save_Completed_Obsid, Load_Completed_Obsids
from merge import Merge_Lightcurves, Split_Rate_Extensions
from logger import Log

# ====================================================================================================
# Build config - 
# ====================================================================================================

USER_CONFIG = Make_User_Config()


Validate_User_Config(USER_CONFIG)

CONFIG = Make_Config(USER_CONFIG)

print(f"Using energy bands - \n{CONFIG["EBANDS"]}")



log_config = CONFIG.copy()
log_config.pop("OBSIDS", None)

Log(CONFIG,
    f"SWIFT-BAT SURVEY DATA REDUCTION PIPELINE FOR GETTING LIGHT CURVES\n",
    f"RUN ID : {CONFIG['RUN_ID']}\n",
    f"Start time : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n",
    f"Configuration : \n{log_config}\n")

# This is to prevent some heasoft tasks from sending a prompt and crashing the pipeline -

ENV = os.environ.copy()
ENV["HEADASNOQUERY"] = "YES"
ENV["HEADASPROMPT"] = "/dev/null"

# Check Save state -

COMPLETED_FILE = os.path.join(CONFIG["LOGPATH"], "completed_obsids.txt")
success_obsids_file = os.path.join(CONFIG["LOGPATH"], "success_obsids.txt")
low_energy_obsids_file = os.path.join(CONFIG["LOGPATH"], "low_energy_obsids.txt")

if CONFIG["INCLUDE_VALIDATION"] == True:

    if CONFIG["CLOBBER"] == "YES":

        Log(CONFIG,
            "Clobber=YES (overwriting save state files)\n")
        
        completed_obsids = set()
        with open(COMPLETED_FILE, "w"):
            pass
        
        with open(success_obsids_file, "w"):
            pass

        with open(low_energy_obsids_file, "w"):
            pass

    else:
        Log(CONFIG,
            f"Clobber=NO, ignoring observations in {COMPLETED_FILE}. \n")
        
        completed_obsids = Load_Completed_Obsids(COMPLETED_FILE)
        
        CONFIG["OBSIDS"] = [
            obsid
            for obsid in CONFIG["OBSIDS"]
            if obsid not in completed_obsids
        ]


    # Pick out only valid obsids -
    Log(CONFIG,
        f"Validating observations ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})")
    
    CONFIG["OBSIDS"] = Valid_Obsids(CONFIG)

    Log(CONFIG,
        f"Validation completed ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})",
        f"Processing {len(CONFIG['OBSIDS'])} Observations.\n",
        "=" * 50)

else:
    CONFIG["OBSIDS"] = [
        obsid
        for obsid in Load_Completed_Obsids(COMPLETED_FILE)
    ]




# ====================================================================================================
# ====================================================================================================
# FILTERS APPLIED BEFORE THIS POINT IN CODE - 

# 1. obsids with more than one required file like attitude file or cal file, etc.
# 2. OBSIDS with missing files.
# 3. if clobber = YES, then clear the save file and start fresh.
# 4. if clobber = NO, consult the save file to check for completed obsids and remove them from the validation check.
# 5. remove obsids which do not fall inside the tstart to tstop duration.
# 6. remove only low energy files (the 'e20' dph). This exclusion is only temporary. Later make a helper function
#       that checks for the input energy bands, and includes the obsid  only for the ebands it is not relevant.
# 7. obsids with no dph files.  
# ====================================================================================================
# ====================================================================================================

# ====================================================================================================
# Main Reduction Loop - 
# ====================================================================================================


if CONFIG["INCLUDE_REDUCTION"] == True:


    for i, obsid in enumerate(CONFIG["OBSIDS"], start=1):
        
        CWD = CONFIG["INPATH"]

        print(f"\nProcessing {obsid} ({i}/{len(CONFIG['OBSIDS'])})")

        start_time = time.perf_counter()
        
        Log(CONFIG,
            f"OBSID : {obsid} ({i}/{len(CONFIG['OBSIDS'])})",
            f"Started : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}")

        try:
            for TASK in Generate_Tasks(CONFIG, obsid):
            
                Run_Command(CONFIG, TASK, CWD, ENV)

                Verify_Output(CONFIG, TASK, CWD)

                Log(CONFIG,
                    "#" * 50)

            Save_Completed_Obsid(obsid, success_obsids_file)
        
        except (subprocess.CalledProcessError, FileNotFoundError, NoGTIError):
            print(f"skipping {obsid}\n")

            Log(CONFIG,
                f"\nSKIPPING {obsid}\n")


        end_time = time.perf_counter()
        execution_time = end_time - start_time

        print(f"\n{obsid} completed in {execution_time:.1f} seconds.\n")

        Log(CONFIG,
            f"\n{obsid} completed in {execution_time:.1f} seconds.\n",
            "=" * 50)

        Save_Completed_Obsid(obsid, COMPLETED_FILE)


    print("processing completed.\n")
    Log(CONFIG,
        f"Processing completed ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})",
        "Proceeding to merging...\n",
        "=" * 60)

else:
    print("Skipping Reduction Process.\n")

# ====================================================================================================
# Merge into a single master lc file - 
# ====================================================================================================


with open(success_obsids_file, "r") as f:
    success_obsids = f.read().splitlines()

if len(success_obsids) == 0:
    Log(CONFIG,
        "Terminating pipeline - \nNo lc files to merge found.")
    
    sys.exit("Terminating pipeline - \nNo lc files to merge found.")

else:
    Log(CONFIG,
        "Merging light curves - ")
    
    print("Open file descriptors:", len(os.listdir(f"/proc/{os.getpid()}/fd")))

    Merge_Lightcurves(CONFIG, success_obsids)

    MASTER_LC = "master_lc.fits"

    print("Files merged. Proceeding to rebinning.\n")
    Log(CONFIG,
        f"Merging completed ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})",
        "Proceeding to rebinning...\n",
        "#" * 50)


    # ====================================================================================================
    # Rebin the lightcurve - 
    # ====================================================================================================
    rebin_task = Rebin_Lightcurve(CONFIG, MASTER_LC)

    print(f"Running {rebin_task.name}")

    Log(CONFIG,
        f"Running {rebin_task.name} ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})\n")

    success_rebinning = True

    try:
        Run_Command(CONFIG, rebin_task, cwd=CONFIG["OUTPATH"], env=ENV)
        
        Verify_Output(CONFIG, rebin_task, cwd=CONFIG["OUTPATH"])

        print("Master file rebinned. Proceeding to splitting.\n")

        Log(CONFIG,
            f"Rebinning completed ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})",
            "#" * 50)

    except subprocess.CalledProcessError:
        print(f"Rebinning failed.\n")
        Log(CONFIG,
            f"Rebinning failed ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})",
            "TERMINATING PIPELINE\n",
            "#" * 50)
        
        success_rebinning = False

    # ====================================================================================================
    # Modify rebinned lightcurve - 
    # ====================================================================================================
    if success_rebinning == True:
        Log(CONFIG,
            "Splitting RATE extensions -")
        
        Split_Rate_Extensions(CONFIG)

        Log(CONFIG,
            "Pipeline run successful.\n",
            "=" * 60)

        print("Pipeline run successful.\n")


    Log(CONFIG,
        f"Pipeline Run completed.",
        f"END TIME : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}")
