from dataclasses import dataclass
import glob
import os

from constants import GLOBAL_EMIN, GLOBAL_EMAX
from logger import Log

@dataclass
class Task:
    name: str
    command: list[str]
    expected_output: str | None = None

@dataclass
class Dph:
    path: str
    file: str
    tag: str


# ====================================================================================================
# BUILD TASKS -
# batsurvey-erebin, batsurvey-gti, batsurvey-aspect, batbinevt_dpi, batsurvey-detmask, batmaskwtimg, batbinevt_lc
# ====================================================================================================


def Generate_Tasks(config, obsid):

    # obs_path = f"{config["INPATH"]}/{obsid}/bat/survey"
    # obs_path = config["OBSDIR_DIR"]

    # Fetch required files - 
    cwd = config["INPATH"]

    dphs = [
        Dph(
            path=os.path.relpath(os.path.dirname(f), start=cwd),
            file=os.path.basename(f),
            tag=os.path.basename(f).replace(".dph.gz", "").replace(".dph", "")
        )
        for f in glob.glob(f"{cwd}/{obsid}/bat/survey/*.dph*")
        if "erebin" not in f
    ]

    detmask_file = os.path.relpath(glob.glob(f"{cwd}/{obsid}/bat/hk/*decb.hk.gz")[0], start=cwd)

    cal_matches = glob.glob(f"{cwd}/{obsid}/bat/hk/*gocb.hk.gz")

    if cal_matches:
        cal_file = os.path.relpath(cal_matches[0], start=cwd)

    else:
        Log(config,
            f"Calibration file (*gocb.hk.gz) for {obsid} not found. Assuming detmask file (*decb.hk.gz) as calibration file.\n")
        cal_file = detmask_file

    attitude_file = os.path.relpath(glob.glob(f"{cwd}/{obsid}/auxil/*sat.fits.gz")[0], start=cwd)


    # ====================================================================================================
    # 1. batsurvey-erebin
    # ====================================================================================================

    for dph in dphs:

        dph_erebin = f"{dph.path}/{dph.tag}_erebin.dph"
        
        yield Task(
            name="1. batsurvey-erebin",

            command=[
                "batsurvey-erebin",
                f"infile={dph.path}/{dph.file}",
                f"outfile={dph_erebin}",
                f"calfile={cal_file}",
                # f"detmask={detmask_file}", # I dont know if providing this actualy makes the analysis more accurate.
                f"baterebin_opts=lowecare={GLOBAL_EMIN} highecare={GLOBAL_EMAX} ebins={config['HEASOFT_EBANDS']}",
                "clobber=YES"
            ],

            expected_output=dph_erebin
        )


    # ====================================================================================================
    # 2. batsurvey-gti
    # ====================================================================================================

    gti_dir = f"{dph.path}/gti_directory"

    yield Task(
        name="2. batsurvey-gti",

        command=[
            "batsurvey-gti",
            f"indir={obsid}",
            f"dphfiles={','.join(f'{dph.path}/{dph.tag}_erebin.dph' for dph in dphs)}",
            f"outdir={gti_dir}",
            f"elimits={GLOBAL_EMIN}-{GLOBAL_EMAX}",
            "detthresh=10000",
            f"ra={config['RA']}",
            f"dec={config['DEC']}",
            "clobber=YES"
        ],

        expected_output=f"{gti_dir}/master.gti"
    )


    # ====================================================================================================
    # 3. batsurvey-aspect
    # ====================================================================================================

    master_gti_file = f"{gti_dir}/master2.gti"
    master_att_file = f"{gti_dir}/{obsid}_attitude.att"

    yield Task(
        name="3. batsurvey-aspect",

        command=[
            "batsurvey-aspect",
            f"gtifile={gti_dir}/master.gti",
            f"attfile={attitude_file}",
            f"outattfile={master_att_file}",
            f"outgtifile={master_gti_file}",
            "clobber=YES"
        ],
        # modify the check to have  multiple output files such as here I need to check master att file too.
        expected_output=master_gti_file
    )

    # ====================================================================================================
    # 4-7. DPH based tasks
    # ====================================================================================================

    for dph in dphs:

        dph_erebin = f"{dph.path}/{dph.tag}_erebin.dph"

        # 4. batbinevt DPI

        dpi_file = f"{dph.path}/total_{dph.tag}.dpi"

        yield Task(
            name="4. batbinevt_dpi",

            command=[
                "batbinevt",
                # f"infile={dph.path}/{dph.file}",
                f"infile={dph_erebin}",
                f"outfile={dpi_file}",
                "outtype=DPI",
                "timedel=0",
                "timebinalg=infile",
                f"energybins={config['HEASOFT_EBANDS']}",
                "clobber=YES"
            ],

            expected_output=dpi_file
        )
  


        # 5. batsurvey-detmask

        master_detmask_file = f"{dph.path}/master_{dph.tag}.detmask"

        yield Task(
            name="5. batsurvey-detmask",

            command=[
                "batsurvey-detmask",
                f"infile={dpi_file}",
                f"outfile={master_detmask_file}",
                f"detflagfile={detmask_file}",
                "clobber=YES"
            ],

            expected_output=master_detmask_file
        )


        # 6. batmaskwtimg

        maskwtimg_file = f"{dph.path}/maskwt_{dph.tag}.img"

        yield Task(
            name="6. batmaskwtimg",

            command=[
                "batmaskwtimg",
                f"infile={dpi_file}",
                f"outfile={maskwtimg_file}",
                f"attitude={master_att_file}",
                f"ra={config['RA']}",
                f"dec={config['DEC']}",
                f"detmask={master_detmask_file}",
                "clobber=YES"
            ],

            expected_output=maskwtimg_file
        )


        # 7. batbinevt LC

        lc_file = f"{dph.path}/outfile_{dph.tag}.lc"

        yield Task(
            name="7. batbinevt_lc",

            command=[
                "batbinevt",
                f"infile={dph_erebin}",
                f"outfile={lc_file}",
                "outtype=LC",
                "timebinalg=gti",
                f"gtifile={master_gti_file}",
                f"energybins={config['HEASOFT_EBANDS']}",
                f"maskwt={maskwtimg_file}",
                f"detmask={master_detmask_file}",
                "outunits=rate",
                "clobber=YES"
            ],

            expected_output=lc_file
        )


def Rebin_Lightcurve(config, master_lc):
    task_rebingausslc = Task(
        name="rebingausslc",

        command=[
            "rebingausslc",
            f"infile={master_lc}",
            f"outfile=master_rebinned.lc",
            f"timedel={config["NEWBIN"]}",
            f"timebinalg=uniform",
            "tstart=INDEF",
            "tstop=INDEF",
            # f"ratecol=RATE",
            # f"errcol=ERROR{i}",
            "clobber=YES"
        ],

        expected_output="master_rebinned.lc"
    )

    return task_rebingausslc

# ====================================================================================================
# Backup Task for historical development reasons -
# ====================================================================================================

# def Generate_Tasks_BACKUP(config, obsid):

#     # obs_path = f"{config["INPATH"]}/{obsid}/bat/survey"
#     obs_path = config["OBSDIR_DIR"]

#     # Fetch required files - 

#     dph_files = [
#     os.path.basename(f)
#     for f in glob.glob(f"{obs_path}/{obsid}/bat/survey/*.dph*")
#     if "erebin" not in f
#     ]    


#     dphs = [
#         Dph(
#         file=dph,
#         tag=dph.replace(".dph.gz", "").replace(".dph", "")
#         )
#         for dph in dph_files
#     ]

#     detmask_file = os.path.relpath(glob.glob(f"{obs_path}/{obsid}/bat/hk/*decb.hk.gz")[0], start=obs_path)

#     cal_matches = glob.glob(f"{obs_path}/{obsid}/bat/hk/*gocb.hk.gz")

#     if cal_matches:
#         cal_file = os.path.relpath(cal_matches[0], start=obs_path)
#     else:
#         cal_file = detmask_file

#     attitude_file = os.path.relpath(glob.glob(f"{obs_path}/{obsid}/auxil/*sat.fits.gz")[0], start=obs_path)


#     # ====================================================================================================
#     # Start yieling tasks - 
#     # ====================================================================================================

#     # 1. batsurvey-erebin

#     for dph in dphs:

#         dph_erebin = f"{dph.tag}_erebin.dph"    
        
#         yield Task(
#             name="batsurvey-erebin",

#             command=[
#                 "batsurvey-erebin",
#                 f"infile={dph.file}",
#                 f"outfile={dph_erebin}",
#                 f"calfile={cal_file}",
#                 # f"detmask={detmask_file}", # I dont know if providing this actualy makes the analysis more accurate.
#                 f"baterebin_opts=lowecare={GLOBAL_EMIN} highecare={GLOBAL_EMAX} ebins={config['HEASOFT_EBANDS']}",
#                 "clobber=YES"
#             ],

#             expected_output=dph_erebin
#         )

#     # 2. batsurvey-gti

#     gti_dir = f"{obs_path}/{obsid}/bat/survey/gti_directory"

#     yield Task(
#         name="batsurvey-gti",

#         command=[
#             f"indir={obsid}",
#             f"dphfiles={','.join(dph.file for dph in dphs)}",
#             f"outdir={gti_dir}",
#             f"elimits={GLOBAL_EMIN}-{GLOBAL_EMAX}",
#             f"ra={config['RA']}",
#             f"dec={config['DEC']}",
#             "clobber=YES"
#         ],

#         expected_output=f"{gti_dir}/pre_master.gti"
#     )


#     # 3. batsurvey-aspect:

#     master_gti_file = f"{gti_dir}/master.gti"

#     yield Task(
#         name="batsurvey-aspect",

#         command=[
#             "batsurvey-aspect",
#             f"gtifile={gti_dir}/pre_master.gti",
#             f"attfile={attitude_file}",
#             f"outattfile={gti_dir}/{obsid}_attitude.att",
#             f"outgtifile={gti_dir}/master.gti",
#             "clobber=YES"
#         ],

#         expected_output=master_gti_file
#     )



#     for dph in dphs:
    
#     # 4. batbinevt (for dpi generation):

#         dpi_file = f"total_{dph.tag}.dpi"

#         yield Task(
#             name="batbinevt_dpi",

#             command=[
#                 "batbinevt",
#                 f"infile={dph.file}",
#                 f"outfile={dpi_file}",
#                 "outtype=DPI",
#                 "timedel=0",
#                 "timebinalg=infile",
#                 f"energybins={config['HEASOFT_EBANDS']}",
#                 "clobber=YES"
#             ],

#             expected_output=dpi_file
#         )        


#     # 5. batsurvey-detmask:
#         master_detmask_file = f"master_{dph.tag}.detmask"
        
#         yield Task(
#             name="batsurvey-detmask",

#             command=[
#                 "batsurvey-detmask",
#                 f"infile={dpi_file}",
#                 f"outfile={master_detmask_file}",
#                 f"detflagfile={detmask_file}",
#                 "clobber=YES"
#             ],

#             expected_output=master_detmask_file
#         )


#     # 6. batmaskwtimg:

#         maskwtimg_file = f"maskwt_{dph.tag}.img"

#         yield Task(
#             name="batmaskwtimg",

#             command=[
#                 "batmaskwtimg",
#                 f"infile={dpi_file}",
#                 f"outfile={maskwtimg_file}",
#                 f"attitude={attitude_file}",
#                 f"ra={config["RA"]}",
#                 f"dec={config["DEC"]}",
#                 f"detmask={master_detmask_file}",
#                 "clobber=YES"            
#             ],

#             expected_output=maskwtimg_file
#         )


#     # 7. batbinevt (for lc generation):

#         lc_file = f"outfile_{dph.tag}.lc"

#         yield Task(
#             name="batbinevt_lc",

#             command=[
#                 "batbinevt",
#                 f"infile={dph_erebin}",
#                 f"outfile={lc_file}",
#                 "outtype=LC",
#                 f"timedel=0",
#                 "timebinalg=infile",
#                 f"energybins={config['HEASOFT_EBANDS']}",
#                 f"maskwt={maskwtimg_file}",
#                 f"detmask={master_detmask_file}",
#                 "outunits=rate",
#                 "clobber=YES"                
#             ],

#             expected_output=lc_file
#         )

# ====================================================================================================
# Task List Built
# ====================================================================================================





# def Reduce_Observation_ad_hoc(config, obsid):

#     tasks = []
    

#     obs_path = f"{config["INPATH"]}/{obsid}/bat/survey"

#     dph_files = [
#     os.path.basename(f)
#     for f in glob.glob(f"{obs_path}/*.dph*")
#     if "erebin" not in f
#     ]


#     detmask_file = os.path.relpath(glob.glob(f"{obs_path}/../hk/*decb.hk.gz")[0], start=obs_path)


#     cal_matches = glob.glob(f"{obs_path}/../hk/*gocb.hk.gz")

#     if cal_matches:
#         cal_file = os.path.relpath(cal_matches[0], start=obs_path)
#     else:
#         cal_file = detmask_file

#     attitude_file = os.path.relpath(glob.glob(f"{obs_path}/../../auxil/*sat.fits.gz")[0], start=obs_path)


#     for dph in dph_files:
        
#         tag = dph.replace(".dph.gz", "").replace(".dph", "")

#         # =========================================================
#         dpi_file = f"total_{tag}.dpi"

#         task_batbinevt_dpi = Task(
#             name="batbinevt_dpi",

#             command=[
#                 "batbinevt",
#                 f"infile={dph}",
#                 f"outfile={dpi_file}",
#                 "outtype=DPI",
#                 "timedel=0",
#                 "timebinalg=infile",
#                 f"energybins={config["HEASOFT_EBANDS"]}",
#                 "clobber=YES"
#             ],

#             expected_output=dpi_file)
        
#         tasks.append(task_batbinevt_dpi)
 
#         # =========================================================
#         master_detmask_file = f"master_{tag}.detmask"
        
#         task_batdetmask = Task(
#             name="batdetmask",

#             command=[
#                 "batdetmask",
#                 f"date={dpi_file}",
#                 f"outfile={master_detmask_file}",
#                 f"detmask={detmask_file}",
#                 "clobber=YES"
#             ],

#             expected_output=master_detmask_file
#         )

#         tasks.append(task_batdetmask)

#         # =========================================================
#         qmap_file = f"total_{tag}.qmap"

#         task_bathotpix = Task(
#             name="bathotpix",

#             command=[
#                 "bathotpix",
#                 f"infile={dpi_file}",
#                 f"outfile={qmap_file}",
#                 f"detmask={master_detmask_file}",
#                 "clobber=YES"
#             ],

#             expected_output=qmap_file
#         )

#         tasks.append(task_bathotpix)

#         # =========================================================
#         maskwtimg_file = f"maskwt_{tag}.img"

#         task_batmastwtimg = Task(
#             name="batmaskwtimg",

#             command=[
#                 "batmaskwtimg",
#                 f"infile={dpi_file}",
#                 f"outfile={maskwtimg_file}",
#                 f"attitude={attitude_file}",
#                 f"ra={config["RA"]}",
#                 f"dec={config["DEC"]}",
#                 f"detmask={master_detmask_file}",
#                 "clobber=YES"
#             ],

#             expected_output=maskwtimg_file
#         )

#         tasks.append(task_batmastwtimg)

#         # =========================================================
#         dph_erebin = f"{tag}_erebin.dph"

#         task_baterebin = Task(
#             name="baterebin",

#             command=[
#                 "baterebin",
#                 f"infile={dph}",
#                 f"outfile={dph_erebin}",
#                 f"calfile={cal_file}",
#                 f"detmask={master_detmask_file}",
#                 f"lowecare={GLOBAL_EMIN}",
#                 f"highecare={GLOBAL_EMAX}",
#                 f"ebins={config["HEASOFT_EBANDS"]}",
#                 "clobber=YES"
#             ],

#             expected_output=dph_erebin
#         )

#         tasks.append(task_baterebin)

#         # =========================================================
#         lc_file = f"outfile_{tag}.lc"

#         task_batbinevt_lc = Task(
#             name="batbinevt_lc",

#             command=[
#                 "batbinevt",
#                 f"infile={dph_erebin}",
#                 f"outfile={lc_file}",
#                 "outtype=LC",
#                 f"timedel=0",
#                 "timebinalg=infile",
#                 f"energybins={config["HEASOFT_EBANDS"]}",
#                 f"maskwt={maskwtimg_file}",
#                 f"detmask={master_detmask_file}",
#                 "outunits=rate",
#                 "clobber=YES"
#             ],

#             expected_output=lc_file
#         )

#         tasks.append(task_batbinevt_lc)


#     return obs_path, tasks

