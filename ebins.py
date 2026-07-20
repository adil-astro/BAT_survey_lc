import numpy as np
from constants import GLOBAL_EMIN, GLOBAL_EMAX


# Stored value of the 80 possible energy bins for BAT instrument
EBOUNDS_ALL = np.array(
    [
        (1, 0.0, 10.0),
        (2, 10.0, 12.0),
        (3, 12.0, 14.0),
        (4, 14.0, 16.0),
        (5, 16.0, 18.0),
        (6, 18.0, 20.0),
        (7, 20.0, 22.0),
        (8, 22.0, 24.0),
        (9, 24.0, 26.0),
        (10, 26.0, 28.0),
        (11, 28.0, 30.1),
        (12, 30.1, 32.1),
        (13, 32.1, 34.2),
        (14, 34.2, 36.3),
        (15, 36.3, 38.3),
        (16, 38.3, 40.4),
        (17, 40.4, 42.5),
        (18, 42.5, 44.6),
        (19, 44.6, 46.8),
        (20, 46.8, 48.9),
        (21, 48.9, 51.1),
        (22, 51.1, 53.2),
        (23, 53.2, 55.4),
        (24, 55.4, 57.6),
        (25, 57.6, 59.8),
        (26, 59.8, 62.0),
        (27, 62.0, 64.2),
        (28, 64.2, 66.4),
        (29, 66.4, 68.7),
        (30, 68.7, 70.9),
        (31, 70.9, 73.2),
        (32, 73.2, 75.4),
        (33, 75.4, 77.7),
        (34, 77.7, 80.0),
        (35, 80.0, 82.3),
        (36, 82.3, 84.6),
        (37, 84.6, 87.0),
        (38, 87.0, 89.3),
        (39, 89.3, 91.7),
        (40, 91.7, 94.0),
        (41, 94.0, 96.4),
        (42, 96.4, 98.8),
        (43, 98.8, 101.2),
        (44, 101.2, 103.6),
        (45, 103.6, 106.0),
        (46, 106.0, 108.4),
        (47, 108.4, 110.9),
        (48, 110.9, 113.3),
        (49, 113.3, 115.8),
        (50, 115.8, 118.2),
        (51, 118.2, 120.7),
        (52, 120.7, 123.2),
        (53, 123.2, 125.7),
        (54, 125.7, 128.3),
        (55, 128.3, 130.8),
        (56, 130.8, 133.3),
        (57, 133.3, 135.9),
        (58, 135.9, 138.4),
        (59, 138.4, 141.0),
        (60, 141.0, 143.6),
        (61, 143.6, 146.2),
        (62, 146.2, 148.8),
        (63, 148.8, 151.4),
        (64, 151.4, 154.1),
        (65, 154.1, 156.7),
        (66, 156.7, 159.4),
        (67, 159.4, 162.0),
        (68, 162.0, 164.7),
        (69, 164.7, 167.4),
        (70, 167.4, 170.1),
        (71, 170.1, 172.8),
        (72, 172.8, 175.5),
        (73, 175.5, 178.2),
        (74, 178.2, 181.0),
        (75, 181.0, 183.7),
        (76, 183.7, 186.5),
        (77, 186.5, 189.3),
        (78, 189.3, 192.1),
        (79, 192.1, 194.9),
        (80, 194.9, 6553.6)
    ],
    dtype=[
        ("CHANNEL", "i4"),
        ("E_MIN", "f4"),
        ("E_MAX", "f4")
    ]
)


def Process_Ebins(input_ebins):
    """
    Process user-defined energy bands into valid BAT energy bands.

    Parameters
    ----------
    input_ebins : str
        User supplied energy bands as a comma-separated string,
        e.g. "14-24,24-51.1,51.1-101.2".

    Returns
    -------
    ebins : np.ndarray
        Corrected, non-overlapping energy bands.

    heasoft_ebins : str
        HEASoft-compatible energy band string.
    """

    # Parse user input

    ebins = [
        tuple(map(float, band.split("-")))
        for band in input_ebins.split(",")
    ]
    
    # Sort by lower energy
    ebins = sorted(ebins, key=lambda x: x[0])
    
    def snap_energy(value, mode="lower"):
        # Apply global limits
        value = max(GLOBAL_EMIN, min(GLOBAL_EMAX, value))

        if mode == "lower":
            allowed = EBOUNDS_ALL["E_MIN"]
            snapped = allowed[allowed <= value].max()

        elif mode == "upper":
            allowed = EBOUNDS_ALL["E_MAX"]
            snapped = allowed[allowed >= value].min()

        else:
            raise ValueError("mode must be 'lower' or 'upper'")

        return float(snapped)

    # Construct final non-overlapping bands
    new_ebounds = []
    last_emax = None

    for emin_user, emax_user in ebins:

        emin_snap = snap_energy(emin_user, mode="lower")
        emax_snap = snap_energy(emax_user, mode="upper")

        # Force exclusivity
        if last_emax is not None and emin_snap < last_emax:
            emin_snap = last_emax

        # Ignore collapsed bands
        if emin_snap >= emax_snap:
            print(f"Ignoring overlapping bin: {emin_user}-{emax_user}")
            continue

        new_ebounds.append((emin_snap, emax_snap))
        last_emax = emax_snap

    ebins = np.array(new_ebounds, dtype=float)

    heasoft_ebins = ",".join(
        f"{emin:.1f}-{emax:.1f}"
        for emin, emax in ebins
    )
    
    return ebins, heasoft_ebins



