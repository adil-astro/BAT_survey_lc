import os
import glob
import sys
from astropy.time import Time
from astropy.io import fits

from logger import Log

def Valid_Obsids(config):

    obsids = config["OBSIDS"]

    cwd = config["INPATH"]

    valid_obsids = obsids.copy()

    low_energy_file = os.path.join(config["LOGPATH"], "low_energy_obsids.txt")

    tstart = Time(config["TSTART"]) if config["TSTART"] else None
    tstop  = Time(config["TSTOP"]) if config["TSTOP"] else None

    for i, obsid in enumerate(obsids, start=1):
        
        print(f"Validating {obsid} ({i}/{len(obsids)})")

        # obs_path = f"{config["INPATH"]}/{obsid}/bat/survey"

        dph_files = [
            f
            for f in glob.glob(f"{cwd}/{obsid}/bat/survey/*.dph*")
            if "erebin" not in f
        ]

        if not dph_files:
            valid_obsids.remove(obsid)
            continue

        
        with fits.open(dph_files[0]) as hdul:

            date_obs = Time(hdul[0].header["DATE-OBS"])
            print(f"Observation Date: {date_obs.isot}\n")

        if tstart is not None and date_obs < tstart:
            valid_obsids.remove(obsid)
            continue

        if tstop is not None and date_obs > tstop:
            valid_obsids.remove(obsid)
            continue


        if any(dph.endswith(("e20.dph.gz", "e20.dph"))
               for dph in dph_files):
            
            with open(low_energy_file, "a") as f:
                f.write(f"{obsid}\n")
            
            # Eventually design pipeline such that these are also included.
            valid_obsids.remove(obsid)
            continue


        detmask_files = glob.glob(f"{cwd}/{obsid}/bat/hk/*decb.hk.gz")
    

        if len(detmask_files) != 1:
            print(f"Skipping {obsid}\n")
            valid_obsids.remove(obsid)
            continue

        # # Ignoring cal_files as they might not be present in every observation.
        # # Use detmask in the reduction code if these dont exist.
        

        cal_files = glob.glob(f"{cwd}/{obsid}/bat/hk/*gocb.hk.gz")

        if len(cal_files) > 1:
            print(f"Skipping {obsid}\n")
            valid_obsids.remove(obsid)
            continue


        attitude_files = glob.glob(f"{cwd}/{obsid}/auxil/*sat.fits.gz")

        if len(attitude_files) != 1:
            print(f"Skipping {obsid}\n")
            valid_obsids.remove(obsid)
            continue


    if not valid_obsids:
        sys.exit(f"TERMINATING PIPELINE -\nNo valid observations found in {config["INPATH"]}")

    else:

        print(f"Rejected {len(obsids) - len(valid_obsids)} observations out of {len(obsids)} observations.")

        Log(config,
            f"Rejected {len(obsids) - len(valid_obsids)} observations out of {len(obsids)} observations.\n")
        
        return valid_obsids
    