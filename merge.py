import numpy as np
import os
import glob
from astropy.io import fits
from astropy.time import Time
from astropy.table import Table
import astropy.units as u
from dataclasses import dataclass

@dataclass
class MergedData:
    TIME: np.ndarray
    RATE: np.ndarray
    ERR: np.ndarray
    TOTCOUNTS: np.ndarray
    FRACEXP: np.ndarray
    TIMEDEL: np.ndarray

    GTI_START: np.ndarray
    GTI_STOP: np.ndarray

    MJDREFI: int
    MJDREFF: float
    MJDREF: float




def met_to_utc(met_timing, correction_factor):
    utc_timing = met_timing + correction_factor
    return utc_timing

def utc_to_mjd(utc_timing, mjdref):
    mjd_timing = mjdref + (utc_timing)/86400
    return mjd_timing

def utc_to_date(utc_timing, mjdref):
    mjd = mjdref + (utc_timing)/86400
    return Time(mjd, format="mjd", scale="utc").isot

def sort_arrays(sort, *arrays):
    return tuple(array[sort] for array in arrays)



# =====================================================================================
def collect_data_from_lc_files(config, obsids):
    # Get the appropriate data for master file
    
    all_time      = []
    all_rate      = []
    all_err       = []
    all_totcounts = []
    all_fracexp   = []
    all_timedel   = []
    all_gti_start = []
    all_gti_stop  = []

    mjdrefi = 51910
    mjdreff = 0.00074287037
    mjdref  = mjdrefi + mjdreff


    # for obsid in config["OBSIDS"]:
    for obsid in obsids:

        obs_path = f"{config["INPATH"]}/{obsid}/bat/survey"
        lc_files = glob.glob(f"{obs_path}/outfile*.lc")

        for lc in lc_files:
            
            with fits.open(lc, memmap=False) as hdul:
                
                data = hdul["RATE"].data
                hdr  = hdul["RATE"].header
                gti  = hdul["STDGTI"].data

                utcf = hdr.get("UTCFINIT", 0.0) # assume 0 correction if it doesnt exist.

                # Copy data from this file.
                
                for row in data:
                    
                    if row["TIMEDEL"] < 100:
                        continue

                    all_rate.append(row["RATE"])
                    all_err.append(row["ERROR"])
                    all_totcounts.append(row["TOTCOUNTS"])
                    all_fracexp.append(row["FRACEXP"])
                    all_timedel.append(row["TIMEDEL"])

                    # Make corrections before copying data of TIME column using this guide - 
                    # https://swift.gsfc.nasa.gov/analysis/suppl_uguide/time_guide.html

                    met_time = row["TIME"]
                    utc_time = met_to_utc(met_time, utcf)

                    all_time.append(utc_time)

                # Convert GTIs to UTC -
                        
                gti_start_met = gti["START"]
                gti_start_utc = met_to_utc(gti_start_met, utcf)
                
                gti_stop_met = gti["STOP"]
                gti_stop_utc = met_to_utc(gti_stop_met, utcf)

                all_gti_start.append(gti_start_utc)
                all_gti_stop.append(gti_stop_utc)



    # Convert to NumPy arrays
    TIME = np.array(all_time)

    RATE = np.vstack(all_rate)

    print(f"Number of LC files: {len(all_rate)}")

    ERR = np.vstack(all_err)
    TOTCOUNTS = np.array(all_totcounts)
    FRACEXP = np.array(all_fracexp)
    TIMEDEL = np.array(all_timedel)

    GTI_START = np.concatenate(all_gti_start)
    GTI_STOP = np.concatenate(all_gti_stop)

    # Sort RATE table rows by TIME
    sort = np.argsort(TIME)

    TIME, RATE, ERR, TOTCOUNTS, FRACEXP, TIMEDEL = sort_arrays(
        sort,
        TIME,
        RATE,
        ERR,
        TOTCOUNTS,
        FRACEXP,
        TIMEDEL,
    )

    # Sort GTIs by START
    gti_sort = np.argsort(GTI_START)

    GTI_START, GTI_STOP = sort_arrays(
        gti_sort,
        GTI_START,
        GTI_STOP,
    )

    return MergedData(
        TIME=TIME,
        RATE=RATE,
        ERR=ERR,
        TOTCOUNTS=TOTCOUNTS,
        FRACEXP=FRACEXP,
        TIMEDEL=TIMEDEL,
        GTI_START=GTI_START,
        GTI_STOP=GTI_STOP,
        MJDREFI=mjdrefi,
        MJDREFF=mjdreff,
        MJDREF=mjdref,
    )
    
# =====================================================================================

def build_single_rate_extension(config, merged):

    # =========================================================
    # Build RATE table
    # =========================================================

    rate_table = Table()

    rate_table["TIME"]      = merged.TIME * u.s
    rate_table["RATE"]      = merged.RATE * 6.25 * (u.count / u.s / u.cm**2)
    rate_table["ERROR"]     = merged.ERR * 6.25 * (u.count / u.s / u.cm**2)
    rate_table["TOTCOUNTS"] = merged.TOTCOUNTS * u.count
    rate_table["FRACEXP"]   = merged.FRACEXP
    rate_table["TIMEDEL"]   = merged.TIMEDEL * u.s

    # =========================================================
    # Build RATE header
    # =========================================================

    rate_hdr = fits.Header()

    rate_hdr["EXTNAME"]  = (
        "RATE",
        "name of this binary table extension"
    )

    rate_hdr["TELESCOP"] = ("SWIFT", "Telescope (mission) name")
    rate_hdr["INSTRUME"] = ("BAT", "Instrument name")
    rate_hdr["OBJECT"]   = (config["SOURCE"], "Source name")
    rate_hdr["RA"]       = (config["RA"], "[deg] R.A. Object")
    rate_hdr["DEC"]      = (config["DEC"], "[deg] Dec Object")
    rate_hdr["EQUINOX"]  = (2000.0, "equinox for ra and dec")
    rate_hdr["RADECSYS"] = ("FK5", "world coord. system for this file (FK5 or FK4)")
    rate_hdr["MJDREFI"]  = (merged.MJDREFI, "integer part of reference time in MJD")
    rate_hdr["MJDREFF"]  = (merged.MJDREFF, "fractional part of reference time in MJD")

    tstart = np.min(merged.TIME)
    tstop  = np.max(merged.TIME)

    tstartf, tstarti = np.modf(tstart)
    tstopf, tstopi   = np.modf(tstop)

    rate_hdr["TSTARTI"] = (tstarti, "integer part of start time")
    rate_hdr["TSTARTF"] = (tstartf, "fractional part of start time")
    rate_hdr["TSTOPI"]  = (tstopi, "integer part of stop time")
    rate_hdr["TSTOPF"]  = (tstopf, "fractional part of stop time")

    rate_hdr["DATE-OBS"] = (utc_to_date(tstart, merged.MJDREF), "TSTART in isot format")
    rate_hdr["DATE-END"] = (utc_to_date(tstop, merged.MJDREF), "TSTOP in isot format")
    rate_hdr["MJD-OBS"]  = (utc_to_mjd(tstart, merged.MJDREF), "TSTART in MJD")
    rate_hdr["MJD-END"]  = (utc_to_mjd(tstop, merged.MJDREF), "TSTOP in MJD")

    rate_hdr["CREATOR"] = ("batbinevt", "Tool that created this file (v 1.49)")
    rate_hdr["DATE"] = (Time.now().utc.isot, "File creation date")
    rate_hdr["TIMVERSN"] = ("OGIP/93-003", "Version of light curve format")

    rate_hdr["EMIN"] = (np.min(config["EBANDS"][:, 0]), "[keV] Lower energy bound")
    rate_hdr["EMAX"] = (np.max(config["EBANDS"][:, 1]), "[keV] Upper energy bound")

    rate_hdr["HDUCLASS"] = ("OGIP", "Conforms to OGIP/GSFC standards")
    rate_hdr["HDUCLAS1"] = ("LIGHTCURVE", "Contains light curve")
    rate_hdr["HDUCLAS2"] = ("NET", "Light curve is background subtracted")
    rate_hdr["HDUCLAS3"] = ("RATE", "Data values are RATE data")

    rate_hdr["TIMESYS"] = ("UTC", "Time system used")
    rate_hdr["TIMEUNIT"] = ("s", "Time unit")
    rate_hdr["TIMEPIXR"] = (0.5, "Time bin alignment")
    rate_hdr["CLOCKCOR"] = ("YES", "if time corrected to UT")

    rate_hdr["TIMEREF"] = ("LOCAL", "Time reference")
    rate_hdr["TASSIGN"] = ("SATELLITE", "Time assigned by clock")

    rate_hdr["TIERRELA"] = (1.0E-8, "[s/s] relative errors expressed as rate")
    rate_hdr["TIERABSO"] = (1.0, "[s] timing precision in second")

    rate_hdr["BACKAPP"] = ("T", "Was background correction applied?")
    rate_hdr["FLUXMETH"] = ("WEIGHTED", "Flux extraction method")
    rate_hdr["DEADC"] = (1.0, "Dead time correction factor")

    return fits.BinTableHDU(
        rate_table,
        header=rate_hdr,
        name="RATE"
    )

# =====================================================================================
def build_primary_extension(rate_hdu):
    primary_hdu = fits.PrimaryHDU()

    keys = [
        "EXTEND",
        "TELESCOP",
        "INSTRUME",
        "OBJECT",
        "RA",
        "DEC",
        "EQUINOX",
        "RADECSYS",
        "TSTARTI",
        "TSTARTF",
        "TSTOPI",
        "TSTOPF",
        "DATE-OBS",
        "DATE-END",
        "MJD-OBS",
        "MJD-END",
        "CREATOR",
        "DATE",
        "TIMVERSN",
    ]

    for key in keys:
        if key in rate_hdu.header:
            primary_hdu.header.append(rate_hdu.header.cards[key])

    return primary_hdu

# =====================================================================================
def build_ebounds_extension(config):
    ebounds_table = Table()

    ebounds_table["CHANNEL"] = np.arange(len(config["EBANDS"]))
    ebounds_table["E_MIN"] = config["EBANDS"][:, 0] * u.keV
    ebounds_table["E_MAX"] = config["EBANDS"][:, 1] * u.keV
    
    # ebounds_hdr = fits.Header()

    ebounds_hdu = fits.BinTableHDU(
        ebounds_table,
        # ebounds_hdr,
        name="EBOUNDS"
    )

    return ebounds_hdu


# =====================================================================================
def build_stdgti_extension(merged):
    
    gti_table = Table()

    gti_table["START"] = merged.GTI_START * u.s
    gti_table["STOP"]  = merged.GTI_STOP * u.s
    
    stdgti_hdu = fits.BinTableHDU(
        gti_table,
        name="STDGTI"
    )

    return stdgti_hdu



# =====================================================================================
def Merge_Lightcurves(config, obsids):
    
    merged_data = collect_data_from_lc_files(config, obsids)

    rate_hdu = build_single_rate_extension(config, merged_data)

    primary_hdu = build_primary_extension(rate_hdu)

    ebounds_hdu = build_ebounds_extension(config)

    stdgti_hdu = build_stdgti_extension(merged_data)

    hdul = fits.HDUList([
        primary_hdu,
        rate_hdu,
        ebounds_hdu,
        stdgti_hdu,
    ])

    master_lc = os.path.join(config["OUTPATH"], "master_lc.fits")

    hdul.writeto(master_lc, overwrite=True)




# =====================================================================================

def Split_Rate_Extensions(config):

    with fits.open(os.path.join(config["OUTPATH"], "master_rebinned.lc")) as hdul:

        primary = hdul["PRIMARY"].copy()
        rate_hdu = hdul["RATE"].copy()
        ebounds = hdul["EBOUNDS"].copy()
        stdgti = hdul["STDGTI"].copy()

        new_hdus = [primary]

        for i, (emin, emax) in enumerate(config["EBANDS"]):

            table = Table()

            table["TIME"]  = rate_hdu.data["TIME"]
            table["RATE"]  = rate_hdu.data["RATE"][:, i]
            table["ERROR"] = rate_hdu.data["ERROR"][:, i]
            table["NSAMP"] = rate_hdu.data["NSAMP"][:, i]

            header = rate_hdu.header.copy()

            header["EXTNAME"] = f"RATE{i+1}"
            header["EMIN"] = emin
            header["EMAX"] = emax

            new_hdus.append(
                fits.BinTableHDU(
                    table,
                    header=header,
                    name=f"RATE{i+1}"
                )
            )

        new_hdus.append(ebounds)
        new_hdus.append(stdgti)

        final_hdul = fits.HDUList(new_hdus)
        
        final_lc = os.path.join(config["OUTPATH"], "FINAL.lc")

        final_hdul.writeto(final_lc, overwrite=True)