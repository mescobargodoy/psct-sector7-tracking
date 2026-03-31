import math

import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time

from ctapipe.coordinates import CameraFrame
from ctapipe.instrument import SubarrayDescription


# ------------------------------------------------------------------
# Hard-coded source database (ICRS, degrees)
# Extracted from VERITAS database
# ------------------------------------------------------------------
SOURCE_DB = {
    "crab": {
        "label": "Crab",
        "ra_deg": 83.63333046211,
        "dec_deg": 22.014471506327,
    },
    "mrk421": {
        "label": "Mrk421",
        "ra_deg": 166.11375231308,
        "dec_deg": 38.208894424657,
    },
    "mrk501": {
        "label": "Mrk501",
        "ra_deg": 253.46747315572,
        "dec_deg": 39.760289932356,
    },
}


# ------------------------------------------------------------------
# Source helpers
# ------------------------------------------------------------------
def get_named_source_coord(source_key):
    """
    Return a hard-coded ICRS SkyCoord for a named source.
    source_key should be one of: 'crab', 'mrk421', 'mrk501'
    """
    key = source_key.strip().lower()

    if key not in SOURCE_DB:
        raise ValueError(f"Unknown source '{source_key}'. Valid options: {list(SOURCE_DB.keys())}")

    entry = SOURCE_DB[key]
    return SkyCoord(
        ra=entry["ra_deg"] * u.deg,
        dec=entry["dec_deg"] * u.deg,
        frame="icrs"
    )


def parse_manual_source(
    ra_deg_text="",
    dec_deg_text="",
    ra_h_text="",
    ra_m_text="",
    ra_s_text="",
    dec_d_text="",
    dec_m_text="",
    dec_s_text=""
):
    """
    Priority:
    1) RA/Dec in degrees if both are filled
    2) RA h/m/s and Dec d/m/s if RA h box is filled
    3) None -> use dropdown source
    """
    try:
        ra_deg_text = ra_deg_text.strip()
        dec_deg_text = dec_deg_text.strip()
        ra_h_text = ra_h_text.strip()
        ra_m_text = ra_m_text.strip()
        ra_s_text = ra_s_text.strip()
        dec_d_text = dec_d_text.strip()
        dec_m_text = dec_m_text.strip()
        dec_s_text = dec_s_text.strip()

        # Degree input takes priority if both are filled
        if ra_deg_text and dec_deg_text:
            return SkyCoord(
                ra=float(ra_deg_text) * u.deg,
                dec=float(dec_deg_text) * u.deg,
                frame="icrs"
            )

        # HMS / DMS input
        if ra_h_text:
            ra_h = float(ra_h_text)
            ra_m = float(ra_m_text or 0.0)
            ra_s = float(ra_s_text or 0.0)

            if dec_d_text == "":
                raise ValueError("If entering RA in h/m/s, please also enter Dec degrees.")

            dec_d = float(dec_d_text)
            dec_m = float(dec_m_text or 0.0)
            dec_s = float(dec_s_text or 0.0)

            dec_sign = -1 if dec_d < 0 else 1

            ra = (ra_h * u.hour) + (ra_m * u.minute) + (ra_s * u.second)
            dec = (abs(dec_d) * u.deg + dec_m * u.arcmin + dec_s * u.arcsec) * dec_sign

            return SkyCoord(ra=ra, dec=dec, frame="icrs")

    except Exception as e:
        raise ValueError(f"Invalid manual coordinate input: {e}")

    return None


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------
def coord_to_table_strings(coord):
    """
    Return a dict of formatted RA/Dec strings for the GUI tables.
    RA shown as h/m/s
    Dec shown as d/m/s
    Seconds are shown to 4 decimals.
    """
    ra = coord.ra.hms
    dec = coord.dec.dms

    if int(dec.d) < 0:
        dec_d_str = f"{int(dec.d):03d}"
    else:
        dec_d_str = f"{int(dec.d):02d}"

    return {
        "ra_h": f"{int(ra.h):02d}",
        "ra_m": f"{int(ra.m):02d}",
        "ra_s": f"{ra.s:.4f}",
        "dec_d": dec_d_str,
        "dec_m": f"{int(dec.m):02d}",
        "dec_s": f"{dec.s:.4f}",
    }


# ------------------------------------------------------------------
# Main tracking calculation
# ------------------------------------------------------------------
def compute_ra_dec_iteratively(
    observation_time,
    observation_run_length,
    source_coord,
):
    """
    Compute required telescope pointing (ICRS) such that the source lands
    at the target camera position.

    Parameters
    ----------
    observation_time : str
        UTC ISO string, e.g. '2025-01-15T03:12:45'
    observation_run_length : astropy.units.Quantity
        e.g. 20 * u.min
    source_coord : SkyCoord
        ICRS source coordinate

    Returns
    -------
    SkyCoord
        Required pointing in ICRS
    """
    # focal length comes from simulation file
    focal_length = 5.586299896240234*u.m
    
    # Define observation time and location. Needed for altaz frame
    obstime_start = Time(observation_time)

    # Code defines observation start as input + run length /2
    # The idea is to compute the RA, Dec such that at the 
    # middle of the run the source is exactly at sector 7
    obstime = obstime_start + observation_run_length / 2
    
    # The coordinates below correspond to the FLWO site where the pSCT is located.
    # Extracted from google maps.
    location = EarthLocation(
        lat=31.674743 * u.deg,
        lon=-110.952792 * u.deg,
        height=1270 * u.m
    )

    # initialize Alt Az frame
    altaz = AltAz(location=location, obstime=obstime)
    
    # transform source RA and Dec to alt/az
    source_coord_altaz = source_coord.transform_to(altaz)
    
    # coordinates below corresponds to center of top middle sector
    camx_target = 0.0 * u.m
    camy_target = 0.27 * u.m

    # define sky coord corresponding to top middle sector center
    # where camera frame origin is centered at the source
    source_coord_in_camera = SkyCoord(
        x=camx_target,
        y=camy_target,
        frame=CameraFrame(
            focal_length=focal_length,
            telescope_pointing=source_coord_altaz
        )
    )
    
    # convert coord to alt/az and then to RA/Dec
    required_pointing_altaz = source_coord_in_camera.transform_to(altaz)
    required_pointing_radec = required_pointing_altaz.transform_to("icrs")
    
    # At this point the source camera coordinates should in principle correspond to
    # the top middle sector center but it is not quite there yet. There is a small
    # delta in x,y which maybe comes from rotations between coordinates.
    # To get to the actual center we now compute this iteratively by adding
    # a correction to the RA/Dec
    deltara = 0.0
    deltadec = 0.0

    for _ in range(1500):
        # apply small correction iteratively to tracking coords
        corrected = SkyCoord(
            ra=required_pointing_radec.ra.value + deltara,
            dec=required_pointing_radec.dec.value + deltadec,
            unit="deg",
            frame="icrs"
        )

        altaz_point = corrected.transform_to(altaz)

        cam_frame = CameraFrame(
            telescope_pointing=altaz_point,
            focal_length=focal_length,
            obstime=obstime,
            location=location,
        )

        source_cam = source_coord.transform_to(cam_frame)
        
        # assess tracking coordinates by comparing to target 
        # x,y values in camera frame
        dx = camx_target - source_cam.x
        dy = camy_target - source_cam.y
        
        # If tolerance reached return coordinate
        # tolerance value was arbitrarily chosen
        if (dx**2 + dy**2)**0.5 < 1e-8 * u.m:
            return corrected

        # calculate small correction to RA and Dec
        deltara += (-dx / focal_length).value * 180 / math.pi
        deltadec += (-dy / focal_length).value * 180 / math.pi

    raise RuntimeError("Did not converge")
