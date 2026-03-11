import math
import tkinter as tk
import tkinter.font as tkfont

import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time

from ctapipe.coordinates import CameraFrame
from ctapipe.instrument import SubarrayDescription


def compute_ra_dec_iteratively(
        source_name,
        observation_time,
        observation_run_length,
):

    subarray = SubarrayDescription.from_hdf(path='pSCT_FLWO_subarray.h5')
    focal_length = subarray.tel[1].optics.equivalent_focal_length

    obstime_start = Time(observation_time)
    obstime = obstime_start + observation_run_length / 2

    location = EarthLocation(
        lat=31.674743 * u.deg,
        lon=-110.952792 * u.deg,
        height=1270 * u.m
    )

    source_coord = SkyCoord.from_name(source_name)

    altaz = AltAz(location=location, obstime=obstime)
    source_coord_altaz = source_coord.transform_to(altaz)

    camx_target = 0.0 * u.m
    camy_target = 0.27 * u.m

    source_coord_in_camera = SkyCoord(
        x=camx_target,
        y=camy_target,
        frame=CameraFrame(
            focal_length=focal_length,
            telescope_pointing=source_coord_altaz
        )
    )

    required_pointing_altaz = source_coord_in_camera.transform_to(altaz)
    required_pointing_radec = required_pointing_altaz.transform_to("icrs")

    offset_pointing_radec = SkyCoord(
        ra=required_pointing_radec.ra.value,
        dec=required_pointing_radec.dec.value,
        unit='deg',
        frame='icrs'
    )

    offset_pointing_altaz = offset_pointing_radec.transform_to(altaz)

    offset_camera_frame = CameraFrame(
        telescope_pointing=offset_pointing_altaz,
        focal_length=focal_length,
        obstime=obstime,
        location=location,
    )

    source_cam_coords = source_coord.transform_to(offset_camera_frame)

    max_iter = 1500
    tolerance = 1e-8
    deltara = 0
    deltadec = 0

    dx = camx_target - source_cam_coords.x
    dy = camy_target - source_cam_coords.y

    for i in range(max_iter):

        corrected_offset_pointing_radec = SkyCoord(
            ra=required_pointing_radec.ra.value + deltara,
            dec=required_pointing_radec.dec.value + deltadec,
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
            return corrected_offset_pointing_radec

        deltara += (-dx / focal_length).value * 180 / math.pi
        deltadec += (-dy / focal_length).value * 180 / math.pi

    raise RuntimeError("Did not converge")


# ---------------- GUI ---------------- #

def run_calculation():

    source_key = source_var.get()

    source_map = {
        "crab": "crab nebula",
        "mrk421": "mrk 421",
        "mrk501": "mrk 501"
    }

    source_name = source_map[source_key]

    time_str = time_entry.get()
    duration = float(duration_entry.get()) * u.min

    utc_date = Time.now().utc.isot.split("T")[0]
    observation_time = f"{utc_date}T{time_str}"

    try:

        coord = compute_ra_dec_iteratively(
            source_name=source_name,
            observation_time=observation_time,
            observation_run_length=duration,
        )

        ra_hours = coord.ra.hms.h
        ra_min = coord.ra.hms.m
        ra_sec = coord.ra.hms.s
        dec_deg = coord.dec.dms.d
        dec_min = coord.dec.dms.m
        dec_sec = coord.dec.dms.s

        result_var.set(
            f"RA: {ra_hours} hours {ra_min} min {ra_sec:.3f} sec\n"
            f"Dec: {dec_deg} degrees {dec_min} min {dec_sec:.3f} sec"
        )

    except Exception as e:
        result_var.set(f"Error: {e}")


# GUI window
root = tk.Tk()
root.title("pSCT Sector7 Pointing Calculator")
root.geometry("600x300")

bigfont = ("Helvetica", 18)
resultfont = ("Helvetica", 22, "bold")

frame = tk.Frame(root, padx=30, pady=30)
frame.pack()

# Source dropdown
tk.Label(frame, text="Source", font=bigfont).grid(row=0, column=0, sticky="W", pady=10)

source_var = tk.StringVar(value="crab")
source_menu = tk.OptionMenu(frame,source_var,"crab", "mrk421", "mrk501")
source_menu.config(font=bigfont)
source_menu.grid(row=0, column=1, pady=10)

# Observation time
utc_date = Time.now().utc.isot.split("T")[0]
tk.Label(
    frame,
    text=f"Run Start (UTC {utc_date} T hh:mm:ss)",
     font=bigfont
).grid(row=1, column=0, sticky="W", pady=10)

time_entry = tk.Entry(frame, font=bigfont, width=12)
time_entry.insert(0, "09:00:00")
time_entry.grid(row=1, column=1, pady=10)

# Run length
tk.Label(frame, text="Run Length (minutes)",font=bigfont).grid(row=2, column=0, sticky="W", pady=10)

duration_entry = tk.Entry(frame, font=bigfont, width=12)
duration_entry.insert(0, "20")
duration_entry.grid(row=2, column=1, pady=10)

# Run button
run_button = tk.Button(frame, text="Compute Pointing", font=bigfont, command=run_calculation)
run_button.grid(row=3, column=0, columnspan=2, pady=20)

# Result
result_var = tk.StringVar()
result_label = tk.Label(frame, textvariable=result_var, font=resultfont, justify="left")
result_label.grid(row=4, column=0, columnspan=2, pady=20)


root.mainloop()