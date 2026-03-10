import math

import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time

from ctapipe.coordinates import CameraFrame
from ctapipe.instrument import SubarrayDescription


def compute_ra_dec_iteratively(
        source_name='crab nebula', 
        observation_time="2025-12-15T09:11",
        observation_run_length=30*u.min,
        return_skycoord=False,
    ):
    """
    Given a source RA and Dec, calculates required pointing such that
    the source is in the top middle sector of SCT camera.

    Parameters
    ----------
    source_name : str, optional
        source name in astropy, by default 'crab nebula'
    observation_time : str, optional
        observation time readable by astropy.Time, by default "2025-12-15T09:01"
    observation_run_length : astropy.units.Quantity, optional
        observation run length in minutes, by default 30 minutes
    return_skycoord : bool, optional
        Whether to return a SkyCoord type object, by default  false

    Returns
    -------
    tuple (RA, Dec)
        RA and Dec pointing required to have source at center of top sector
    """

    subarray = SubarrayDescription.from_hdf(path='pSCT_FLWO_subarray.h5')

    # geometry = CameraGeometry.from_table('pSCT_FLWO_camera_geometry.h5')
    focal_length = subarray.tel[1].optics.equivalent_focal_length

    # Define observation time and location. Needed for altaz frame
    obstime_start = Time(observation_time)
    
    # obstime is the time at which the source will be exactly at the top middle sector center
    obstime = obstime_start+observation_run_length/2

    # Astropy FLWO database coordinaes
    # location = EarthLocation.of_site("flwo")

    # The coordinates below correspond to the FLWO site where the pSCT is located.
    # Extracted from google maps. 
    # Difference between using astropy FLWO database vs google maps coordinates is
    # at the thousands of a degree level likely negliglbe for our purposes.
    location = EarthLocation(lat=31.674743*u.deg, lon=-110.952792*u.deg, height=1270*u.m)

    # Get RA and Dec from a source given its name
    # Make sure it is in astropy database
    source_coord = SkyCoord.from_name(source_name)

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

    # convert camera coord to alt/az
    required_pointing_altaz = source_coord_in_camera.transform_to(altaz)
    
    # convert camera alt/az to RA and Dec
    # We now have the top middle sector center coordinats in RA and Dec
    required_pointing_radec = required_pointing_altaz.transform_to("icrs")

    # Define new coordinates using the RA and Dec corresponding to the 
    # an offset such that the source is now at the top middle sector
    # This will be used to define a new camera frame whose origin
    # is at this new offset pointing
    offset_pointing_radec = SkyCoord(
        ra=required_pointing_radec.ra.value, 
        dec=required_pointing_radec.dec.value, 
        unit='deg', 
        frame='icrs'
    )

    # Transform to offset pointing to alt/az
    offset_pointing_altaz = offset_pointing_radec.transform_to(altaz)

    # Create camera frame where the center of camera is now at offset pointing
    offset_camera_frame = CameraFrame(
        telescope_pointing=offset_pointing_altaz,
        focal_length=focal_length,
        obstime=obstime,
        location=location,
    )

    # Transform source object coordinates to offset pointing camera frame coordinates
    # At this point the source camera coordinates should in principle correspond to
    # the top middle sector center but it is not quite there yet. There is a small
    # delta in x,y which maybe comes from rotations between coordinates. 
    # To get to the actual center we now compute this iteratively by adding 
    # a correction to the RA/Dec
    # In other words our pointing is still not correct.
    source_cam_coords = source_coord.transform_to(offset_camera_frame)

    max_iter = 1500
    tolerance = 1e-8
    deltara = 0
    deltadec = 0

    # Difference in coordinates
    dx = camx_target - source_cam_coords.x
    dy = camy_target - source_cam_coords.y    

    for i in range(max_iter):

        corrected_offset_pointing_radec = SkyCoord(
            ra=required_pointing_radec.ra.value+deltara, 
            dec=required_pointing_radec.dec.value+deltadec, 
            unit='deg', 
            frame='icrs'
        )

        correced_offset_pointing_altaz = corrected_offset_pointing_radec.transform_to(altaz)

        corrected_offset_camera_frame = CameraFrame(
            telescope_pointing=correced_offset_pointing_altaz,
            focal_length=focal_length,
            obstime=obstime,
            location=location,
        )

        corrected_source_cam_coords = source_coord.transform_to(corrected_offset_camera_frame)
            
        dx = camx_target - corrected_source_cam_coords.x
        dy = camy_target - corrected_source_cam_coords.y

        if (dx**2 + dy**2)**0.5 < tolerance * u.m:
            print("Converged!")
            print("Use this RA and Dec as your pointing:")
            ra_hours = corrected_offset_pointing_radec.ra.hms.h
            ra_min = corrected_offset_pointing_radec.ra.hms.m
            ra_sec = corrected_offset_pointing_radec.ra.hms.s
            dec_deg = corrected_offset_pointing_radec.dec.dms.d
            dec_min = corrected_offset_pointing_radec.dec.dms.m
            dec_sec = corrected_offset_pointing_radec.dec.dms.s
            print("RA:", ra_hours, "hours", ra_min, "min", ra_sec, "sec")
            print("Dec:", dec_deg, "degrees", dec_min, "min", dec_sec, "sec")
                
            if return_skycoord == True:
                return corrected_offset_pointing_radec
            
            else:
                return 

        # correction to be added iteratively to RA and Dec
        deltara  += (-dx / focal_length).value*180/math.pi
        deltadec += (-dy / focal_length).value*180/math.pi
        
    return "Did not converge!"