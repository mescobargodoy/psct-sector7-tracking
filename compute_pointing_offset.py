import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time

from ctapipe.coordinates import CameraFrame, TelescopeFrame
from ctapipe.instrument import SubarrayDescription

import numpy as np

from compute_ra_dec_iteratively import compute_ra_dec_iteratively

def compute_pointing_offset(
    source_name='crab nebula',
    observation_time="2025-12-15T09:11",
    obs_run_length = 20*u.min,
    stepsize = 600, 
    ):
    """
    Computes the angular distance between the center of the sector
    and the source position in the field of view.

    Parameters
    ----------
    source_name : str, optional
        source name in astropy, by default 'crab nebula'
    observationtime : str, optional
        observation time readable by astropy.Time, by default "2025-12-15T09:01"
    obs_run_length : astropy.quantitiy, optional
        astropy time quantity, by default 20*u.min
    stepsize : int, optional
        divides observation run simulation in given stepsize, by default 600
    """

    # Subarray object containing telescope description
    # subarray = SubarrayDescription.from_hdf(path='pSCT_FLWO_subarray.h5')
    # focal_length = subarray.tel[1].optics.equivalent_focal_length
    
    # hard coding focal length 
    # this avoids having to read subarray file
    focal_length = 5.586299896240234*u.m 

    # load source coordinates using astropy 
    source_coord = SkyCoord.from_name(source_name)
    obstime = Time(observation_time)

    # astropy has FLWO stored in its database
    location = EarthLocation.of_site("flwo")

    altaz = AltAz(location=location, obstime=obstime)

    pointing = compute_ra_dec_iteratively(
        source_name, 
        observation_time,
        observation_run_length=obs_run_length,
        return_skycoord=True
    )
    pointing_altaz = pointing.transform_to(altaz)

    # center of sector 7 in camera coordinates
    sector7_x = 0.0 * u.m
    sector7_y = 0.27 * u.m

    # Define initial camera frame
    camera_frame = CameraFrame(
        focal_length=focal_length,
        telescope_pointing=pointing_altaz,
        obstime=pointing_altaz.obstime,
        location=pointing_altaz.location,
    )

    # Define intiial telescope frame
    telescope_frame = TelescopeFrame(
        telescope_pointing=pointing_altaz,
        obstime=pointing_altaz.obstime,
        location=pointing_altaz.location,
    )

    sector7_center = SkyCoord(
        x=sector7_x,
        y=sector7_y,
        frame=camera_frame,
    )

    source_coor_telframe = source_coord.transform_to(telescope_frame)
    sector7_center_telframe = sector7_center.transform_to(telescope_frame)
    
    # initializing arrays to be filled later    
    times_arr = np.zeros(stepsize+1)
    time_since_obs_start_arr = np.zeros(stepsize+1)
    angular_separation_arr = np.zeros(stepsize+1)

    # compute zeroth angular separation
    ang_sep = source_coor_telframe.separation(sector7_center_telframe).value

    # compute zeroth angular separation
    time_diff = (obstime-obstime).to_value(u.s)
    
    # Fill arrays zeroth value
    times_arr[0] = obstime.to_value('mjd')
    time_since_obs_start_arr[0] = time_diff
    angular_separation_arr[0] = ang_sep

    # initialize observatiom time variable that will be updated
    obstime_updated = obstime

    # amount to increase observation time by
    delta_t = obs_run_length.to_value(u.s)*u.s/stepsize

    # Loop to start updating observation
    # This updates the telescope alt/az as it slews with time
    for i in range(1,stepsize+1):
        
        obstime_updated += delta_t

        altaz_updated = AltAz(location=location, obstime=obstime_updated)

        pointing_altaz_updated = pointing_altaz.transform_to(altaz_updated)

        # update camera frame as time advances
        camera_frame_updated = CameraFrame(
            focal_length=focal_length,
            telescope_pointing=pointing_altaz_updated,
            obstime=pointing_altaz_updated.obstime,
            location=pointing_altaz_updated.location,
        )

        # update telescope frame as time advances
        telescope_frame_updated = TelescopeFrame(
            telescope_pointing=pointing_altaz_updated,
            obstime=pointing_altaz_updated.obstime,
            location=pointing_altaz_updated.location,
        )

        # update sector 7 coordinates as time advances
        # this one might not be necessary as cam coordinates
        # would be fixed
        sector7_center_updated = SkyCoord(
            x=sector7_x,
            y=sector7_y,
            frame=camera_frame_updated,
        )
        
        # updated source coordinates in telescope frame
        source_coor_telframe_updated = source_coord.transform_to(telescope_frame_updated)
        # updated sector 7 coordinates in telescope frame (should be fixed so this shouldn't matter)
        sector7_center_telframe_updated = sector7_center_updated.transform_to(telescope_frame_updated)

        # compute angular separation between sector 7 center and source in telescope frame
        ang_sep = source_coor_telframe_updated.separation(sector7_center_telframe_updated).value
        time_diff = (obstime_updated-obstime).to_value(u.s)

        # update numpy arrays
        times_arr[i] = obstime_updated.to_value('mjd')
        time_since_obs_start_arr[i] = time_diff
        angular_separation_arr[i] = ang_sep

    return times_arr, time_since_obs_start_arr, angular_separation_arr
