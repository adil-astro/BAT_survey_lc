import argparse
import os
from datetime import datetime
from astropy.time import Time

from ebins import Process_Ebins


def Make_User_Config():

    parser = argparse.ArgumentParser(
        description="Swift-BAT Survey light curves pipeline configuration."
    )

    # =====================================================
    # Essential Parameters
    # =====================================================

    parser.add_argument(
        "--inpath",
        type=str,
        required=True,
        help="Path containing input data."
    )

    parser.add_argument(
        "--outpath",
        type=str,
        required=True,
        help="Path containing output data."
    )

    parser.add_argument(
        "--ra",
        type=float,
        required=True,
        help="Source right ascension (degrees)."
    )

    parser.add_argument(
        "--dec",
        type=float,
        required=True,
        help="Source declination (degrees)."
    )


    # =====================================================
    # Optional Parameters
    # =====================================================

    parser.add_argument(
        "--tstart",
        type=str,
        default=None,
        help="Start date (YYYY-MM-DD)."
    )

    parser.add_argument(
        "--tstop",
        type=str,
        default=None,
        help="Stop date (YYYY-MM-DD)."
    )


    parser.add_argument(
        "--newbin",
        type=int,
        default=86400,
        help="Lightcurve bin size in seconds."
    )


    parser.add_argument(
        "--ebins",
        type=str,
        default="14-24,24-51.1,51.1-101.2,101.2-194.9",
        help="Energy bins as a comma seperated list: 14-50,50-100,100-195. The user can provide arbitrary energy bins between the global maximum and minimum (14.0-194.9)."
    )

    parser.add_argument(
        "--logpath",
        type=str,
        default=None,
        help="Directory containing log files. Default is 'logs' directory inside outpath."
    )

    parser.add_argument(
        "--source",
        type=str,
        default="Object",
        help="The name of source object. spaces in the source name are not allowed."
    )

    parser.add_argument(
        "--clobber",
        type=str,
        default="NO",
        choices=["YES", "NO"],
        help="Overwrite existing files."
    )

    parser.add_argument(
        "--include_validation",
        type=bool,
        default=True,
        help="Run validation check of observation data. This parameter is primarily for development purposes."
    )

    parser.add_argument(
        "--include_reduction",
        type=bool,
        default=True,
        help="Run data reduction process. This is parameter primarily for development purposes."
    )


    args = parser.parse_args()

    if args.logpath is None:
        args.logpath = os.path.join(args.outpath, "logs")

    
    USER_CONFIG = {

        # Essential
        "INPATH": args.inpath,
        "OUTPATH": args.outpath,

        "RA": args.ra,
        "DEC": args.dec,


        # Optional
        "TSTART": args.tstart,
        "TSTOP": args.tstop,

        "NEWBIN": args.newbin,

        "EBINS": args.ebins,
        
        "LOGPATH": args.logpath,

        "SOURCE": args.source,

        "CLOBBER": args.clobber,

        "INCLUDE_VALIDATION": args.include_validation,

        "INCLUDE_REDUCTION": args.include_reduction
    }


    return USER_CONFIG


def Make_Config(user):

    # Essential
    INPATH = user["INPATH"]
    OUTPATH = user["OUTPATH"]

    RA = user["RA"]
    DEC = user["DEC"]

    # Optional
    TSTART = user["TSTART"]
    TSTOP = user["TSTOP"]

    NEWBIN = user["NEWBIN"]

    EBINS = user["EBINS"]

    LOGPATH = user["LOGPATH"]
    os.makedirs(LOGPATH, exist_ok=True)

    SOURCE = user["SOURCE"]
    
    CLOBBER = user["CLOBBER"]

    INCLUDE_VALIDATION = user["INCLUDE_VALIDATION"]

    INCLUDE_REDUCTION = user["INCLUDE_REDUCTION"]

    # Derived
    OBSIDS = os.listdir(INPATH)

    # LOGS_DIR = os.path.join(LOGPATH, "logs")
    

    EBANDS, HEASOFT_EBANDS = Process_Ebins(EBINS)

    RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

    LOG_FILE = os.path.join(LOGPATH, f"batlc_{RUN_ID}.log")

    CONFIG = {
        "INPATH": INPATH,

        "OUTPATH": OUTPATH,

        "RA": RA,

        "DEC": DEC,

        "TSTART": TSTART,

        "TSTOP": TSTOP,

        "NEWBIN": NEWBIN,

        "EBANDS": EBANDS,

        "HEASOFT_EBANDS": HEASOFT_EBANDS,

        "OBSIDS": OBSIDS,

        "RUN_ID": RUN_ID,

        "LOGPATH": LOGPATH,
        
        "LOG_FILE": LOG_FILE,

        "SOURCE": SOURCE,

        "CLOBBER": CLOBBER,

        "INCLUDE_VALIDATION": INCLUDE_VALIDATION,

        "INCLUDE_REDUCTION": INCLUDE_REDUCTION
    }

    return CONFIG



def Validate_User_Config(user):

    # -----------------------------------------------------
    # Paths
    # -----------------------------------------------------

    if not os.path.isdir(user["INPATH"]):
        raise ValueError(
            f"INPATH does not exist:\n{user['INPATH']}"
        )

    if not os.path.isdir(user["OUTPATH"]):
        raise ValueError(
            f"OUTPATH does not exist:\n{user['OUTPATH']}"
        )


    # -----------------------------------------------------
    # Coordinates
    # -----------------------------------------------------

    if not (0.0 <= user["RA"] < 360.0):
        raise ValueError(
            "RA must lie between 0 and 360 degrees."
        )

    if not (-90.0 <= user["DEC"] <= 90.0):
        raise ValueError(
            "DEC must lie between -90 and 90 degrees."
        )


    # -----------------------------------------------------
    # Dates
    # -----------------------------------------------------

    if user["TSTART"] is not None:
        try:
            Time(user["TSTART"])
        except Exception:
            raise ValueError(
                "TSTART must be in YYYY-MM-DD format."
            )

    if user["TSTOP"] is not None:
        try:
            Time(user["TSTOP"])
        except Exception:
            raise ValueError(
                "TSTOP must be in YYYY-MM-DD format."
            )

    if user["TSTART"] is not None and user["TSTOP"] is not None:

        if Time(user["TSTART"]) >= Time(user["TSTOP"]):
            raise ValueError(
                "TSTART must be earlier than TSTOP."
            )


    # -----------------------------------------------------
    # Lightcurve
    # -----------------------------------------------------

    if user["NEWBIN"] <= 0:
        raise ValueError(
            "NEWBIN must be a positive integer."
        )


    # -----------------------------------------------------
    # Energy bins
    # -----------------------------------------------------

    try:

        ebins = []

        for band in user["EBINS"].split(","):

            limits = band.split("-")

            if len(limits) != 2:
                raise ValueError

            low, high = map(float, limits)

            ebins.append((low, high))
        

    except Exception:
        raise ValueError(
            "Energy bins must be specified like "
            "14-24,24-51.1,51.1-101.2,101.2-194.9"
        )
    
    if len(ebins) > 80:
        raise ValueError(
            "A maximum of 80 energy bands is allowed."
        )
    
    for low, high in ebins:

        if low >= high:
            raise ValueError(
                "Lower energy limit must be smaller than upper limit."
            )
