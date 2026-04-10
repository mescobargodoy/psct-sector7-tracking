import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

import astropy.units as u
from astropy.time import Time

from tracking_math import (
    compute_ra_dec_iteratively,
    get_named_source_coord,
    parse_manual_source,
    coord_to_table_strings,
)

from datetime import datetime

# ------------------------------------------------------------------
# Log helper functions
# ------------------------------------------------------------------

def write_log(
    observation_time,
    duration,
    source_name,
    manual_input_used,
    manual_inputs,
    source_coord,
    tracking_coord
):
    log_file = "tracking_tools_log.txt"

    timestamp = datetime.utcnow().isoformat()

    with open(log_file, "a") as f:
        f.write("=" * 50 + "\n")
        f.write(f"Log Time (UTC): {timestamp}\n")
        f.write(f"Run Start (UTC): {observation_time}\n")
        f.write(f"Run Length (min): {duration.value}\n\n")

        f.write(f"Source Selected: {source_name}\n")
        f.write(f"Manual Input Used: {manual_input_used}\n")

        if manual_input_used:
            f.write(f"Manual Inputs: {manual_inputs}\n")

        f.write("\nSource Coordinates:\n")
        f.write(source_coord.to_string("hmsdms") + "\n")

        f.write("\nTracking Coordinates:\n")
        f.write(tracking_coord.to_string("hmsdms") + "\n")

        f.write("\n")

# ------------------------------------------------------------------
# GUI helper functions
# ------------------------------------------------------------------
def clear_result_table():
    # Tracking coordinates
    track_ra_h_var.set("")
    track_ra_m_var.set("")
    track_ra_s_var.set("")
    track_dec_d_var.set("")
    track_dec_m_var.set("")
    track_dec_s_var.set("")

    # Source coordinates
    src_ra_h_var.set("")
    src_ra_m_var.set("")
    src_ra_s_var.set("")
    src_dec_d_var.set("")
    src_dec_m_var.set("")
    src_dec_s_var.set("")

    error_var.set("")


def fill_table(coord, ra_h_var, ra_m_var, ra_s_var, dec_d_var, dec_m_var, dec_s_var):
    parts = coord_to_table_strings(coord)

    ra_h_var.set(parts["ra_h"])
    ra_m_var.set(parts["ra_m"])
    ra_s_var.set(parts["ra_s"])
    dec_d_var.set(parts["dec_d"])
    dec_m_var.set(parts["dec_m"])
    dec_s_var.set(parts["dec_s"])


def get_manual_source_from_gui():
    return parse_manual_source(
        ra_deg_text=ra_deg_entry.get(),
        dec_deg_text=dec_deg_entry.get(),
        ra_h_text=ra_h_entry.get(),
        ra_m_text=ra_m_entry.get(),
        ra_s_text=ra_s_entry.get(),
        dec_d_text=dec_d_entry.get(),
        dec_m_text=dec_m_entry.get(),
        dec_s_text=dec_s_entry.get(),
    )


def run_calculation():
    clear_result_table()

    try:
        duration = float(duration_entry.get().strip()) * u.min
        time_str = time_entry.get().strip()

        utc_date = Time.now().utc.isot.split("T")[0]
        observation_time = f"{utc_date}T{time_str}"

        # Priority: manual input first, otherwise dropdown source
        source_coord = get_manual_source_from_gui()

        if source_coord is None:
            selected = source_var.get().strip().lower()

            if selected == "none":
                raise ValueError("Please select a source from the dropdown or enter manual coordinates.")

            source_coord = get_named_source_coord(selected)

        # Compute tracking coordinates
        tracking_coord = compute_ra_dec_iteratively(
            observation_time=observation_time,
            observation_run_length=duration,
            source_coord=source_coord,
        )
        
       # Determine if manual input was used
        manual_input_used = source_coord is not None and (
            ra_deg_entry.get().strip() != "" or
            dec_deg_entry.get().strip() != "" or
            ra_h_entry.get().strip() != ""
        )

        source_name = source_var.get().strip().lower()

        manual_inputs = {
            "ra_deg": ra_deg_entry.get(),
            "dec_deg": dec_deg_entry.get(),
            "ra_h": ra_h_entry.get(),
            "ra_m": ra_m_entry.get(),
            "ra_s": ra_s_entry.get(),
            "dec_d": dec_d_entry.get(),
            "dec_m": dec_m_entry.get(),
            "dec_s": dec_s_entry.get(),
        }

        # Write log
        write_log(
            observation_time=observation_time,
            duration=duration,
            source_name=source_name,
            manual_input_used=manual_input_used,
            manual_inputs=manual_inputs,
            source_coord=source_coord,
            tracking_coord=tracking_coord,
        )

        # Fill tracking table
        fill_table(
            tracking_coord,
            track_ra_h_var, track_ra_m_var, track_ra_s_var,
            track_dec_d_var, track_dec_m_var, track_dec_s_var
        )

        # Fill source table
        fill_table(
            source_coord,
            src_ra_h_var, src_ra_m_var, src_ra_s_var,
            src_dec_d_var, src_dec_m_var, src_dec_s_var
        )

    except Exception as e:
        clear_result_table()
        error_var.set(f"Error: {e}")


# ------------------------------------------------------------------
# Window
# ------------------------------------------------------------------
root = tk.Tk()
root.title("pSCT Sector7 Tracking Calculator")
root.geometry("600x580")

# Fonts
font = tkfont.Font(family="Arial", size=12)
header_font = tkfont.Font(family="Arial", size=13, weight="bold")
section_font = tkfont.Font(family="Arial", size=12, weight="bold")
small_font = tkfont.Font(family="Arial", size=11)
track_title_font = tkfont.Font(family="Arial", size=14, weight="bold")
value_font = tkfont.Font(family="Arial", size=12, weight="bold")

# Main frame
frame = ttk.Frame(root, padding=20)
frame.grid(sticky="nsew")

current_row = 0

# ------------------------------------------------------------------
# INPUT SECTION
# ------------------------------------------------------------------

# Instructions for drop down menu selection
ttk.Label(
    frame,
    text="Select source from the drop down menu",
    font=section_font
).grid(row=current_row, column=0, columnspan=10, sticky="w", pady=(0, 6))
current_row += 1

# Source dropdown
ttk.Label(frame, text="Source", font=font).grid(row=current_row, column=0, sticky="w", padx=(0, 4))
source_var = tk.StringVar(value="none")

source_menu = ttk.Combobox(
    frame,
    textvariable=source_var,
    values=["none", "crab", "mrk421", "mrk501"],
    state="readonly",
    width=18
)
source_menu.grid(row=current_row, column=1, columnspan=2, sticky="w", pady=(0, 14))
source_menu.current(0)
current_row += 1

# Instructions for manual RA/Dec
ttk.Label(
    frame,
    text="Or input the coordinates (RA and Dec) manually in the boxes",
    font=section_font
).grid(row=current_row, column=0, columnspan=10, sticky="w", pady=(0, 6))
current_row += 1

# RA manual h/m/s
ttk.Label(frame, text="RA", font=font).grid(row=current_row, column=0, sticky="w", padx=(0, 2))

ra_h_entry = ttk.Entry(frame, width=7)
ra_h_entry.grid(row=current_row, column=1, sticky="w", padx=(0, 1))
ttk.Label(frame, text="hours", font=small_font).grid(row=current_row, column=2, sticky="w", padx=(1, 6))

ra_m_entry = ttk.Entry(frame, width=7)
ra_m_entry.grid(row=current_row, column=3, sticky="w", padx=(0, 1))
ttk.Label(frame, text="min", font=small_font).grid(row=current_row, column=4, sticky="w", padx=(1, 6))

ra_s_entry = ttk.Entry(frame, width=9)
ra_s_entry.grid(row=current_row, column=5, sticky="w", padx=(0, 1))
ttk.Label(frame, text="sec", font=small_font).grid(row=current_row, column=6, sticky="w", padx=(1, 0))

current_row += 1

# Dec manual d/m/s
ttk.Label(frame, text="Dec", font=font).grid(row=current_row, column=0, sticky="w", padx=(0, 2))

dec_d_entry = ttk.Entry(frame, width=7)
dec_d_entry.grid(row=current_row, column=1, sticky="w", padx=(0, 1))
ttk.Label(frame, text="deg", font=small_font).grid(row=current_row, column=2, sticky="w", padx=(1, 6))

dec_m_entry = ttk.Entry(frame, width=7)
dec_m_entry.grid(row=current_row, column=3, sticky="w", padx=(0, 1))
ttk.Label(frame, text="min", font=small_font).grid(row=current_row, column=4, sticky="w", padx=(1, 6))

dec_s_entry = ttk.Entry(frame, width=9)
dec_s_entry.grid(row=current_row, column=5, sticky="w", padx=(0, 1))
ttk.Label(frame, text="sec", font=small_font).grid(row=current_row, column=6, sticky="w", padx=(1, 0))

current_row += 1

# Degree-only section
ttk.Label(
    frame,
    text="Or in degrees",
    font=section_font
).grid(row=current_row, column=0, columnspan=10, sticky="w", pady=(14, 6))
current_row += 1

ttk.Label(frame, text="RA", font=font).grid(row=current_row, column=0, sticky="w", padx=(0, 2))
ra_deg_entry = ttk.Entry(frame, width=10)
ra_deg_entry.grid(row=current_row, column=1, sticky="w", padx=(0, 1))
ttk.Label(frame, text="degrees", font=small_font).grid(row=current_row, column=2, sticky="w", padx=(1, 0))
current_row += 1

ttk.Label(frame, text="Dec", font=font).grid(row=current_row, column=0, sticky="w", padx=(0, 2))
dec_deg_entry = ttk.Entry(frame, width=10)
dec_deg_entry.grid(row=current_row, column=1, sticky="w", padx=(0, 1))
ttk.Label(frame, text="degrees", font=small_font).grid(row=current_row, column=2, sticky="w", padx=(1, 0))
current_row += 1

# Observation time
utc_date = Time.now().utc.isot.split("T")[0]
default_utc_time = Time.now().utc.isot.split("T")[1].split(".")[0]

ttk.Label(
    frame,
    text=f"Run Start (UTC {utc_date}Thh:mm:ss)",
    font=font
).grid(row=current_row, column=0, columnspan=2, sticky="w", pady=(16, 0))

time_entry = ttk.Entry(frame, width=14)
time_entry.insert(0, default_utc_time)
time_entry.grid(row=current_row, column=2, sticky="w", pady=(16, 0))
current_row += 1

# Run length
ttk.Label(frame, text="Run Length (min)", font=font).grid(
    row=current_row, column=0, columnspan=2, sticky="w", pady=(8, 0)
)

duration_entry = ttk.Entry(frame, width=14)
duration_entry.insert(0, "20")
duration_entry.grid(row=current_row, column=2, sticky="w", pady=(8, 0))
current_row += 1

# Extra vertical space before button
ttk.Label(frame, text="").grid(row=current_row, column=0, pady=(8, 8))
current_row += 1

# Compute button
ttk.Button(
    frame,
    text="Compute Pointing",
    command=run_calculation
).grid(row=current_row, column=0, columnspan=10, pady=(0, 0))
current_row += 1

# Error display
error_var = tk.StringVar()
ttk.Label(frame, textvariable=error_var, foreground="red", font=small_font).grid(
    row=current_row, column=0, columnspan=10, sticky="w", pady=(6, 4)
)
current_row += 1

# ------------------------------------------------------------------
# TRACKING OUTPUT (highlighted)
# ------------------------------------------------------------------
tracking_frame = ttk.LabelFrame(frame, text=" Tracking Coordinates ", padding=12)
tracking_frame.grid(row=current_row, column=0, columnspan=10, sticky="w", pady=(0, 10))
current_row += 1

ttk.Label(tracking_frame, text="RA", font=track_title_font).grid(row=0, column=0, sticky="w", padx=(14, 26))
ttk.Label(tracking_frame, text="Dec", font=track_title_font).grid(row=0, column=2, sticky="w", padx=(14, 0))

# Tracking StringVars
track_ra_h_var = tk.StringVar()
track_ra_m_var = tk.StringVar()
track_ra_s_var = tk.StringVar()

track_dec_d_var = tk.StringVar()
track_dec_m_var = tk.StringVar()
track_dec_s_var = tk.StringVar()

# Row 1
ttk.Label(tracking_frame, textvariable=track_ra_h_var, font=value_font).grid(row=1, column=0, sticky="w", padx=(14, 3))
ttk.Label(tracking_frame, text="hours", font=font).grid(row=1, column=1, sticky="w", padx=(0, 18))

ttk.Label(tracking_frame, textvariable=track_dec_d_var, font=value_font).grid(row=1, column=2, sticky="w", padx=(14, 3))
ttk.Label(tracking_frame, text="deg", font=font).grid(row=1, column=3, sticky="w")

# Row 2
ttk.Label(tracking_frame, textvariable=track_ra_m_var, font=value_font).grid(row=2, column=0, sticky="w", padx=(14, 3))
ttk.Label(tracking_frame, text="min", font=font).grid(row=2, column=1, sticky="w", padx=(0, 18))

ttk.Label(tracking_frame, textvariable=track_dec_m_var, font=value_font).grid(row=2, column=2, sticky="w", padx=(14, 3))
ttk.Label(tracking_frame, text="min", font=font).grid(row=2, column=3, sticky="w")

# Row 3
ttk.Label(tracking_frame, textvariable=track_ra_s_var, font=value_font).grid(row=3, column=0, sticky="w", padx=(14, 3))
ttk.Label(tracking_frame, text="sec", font=font).grid(row=3, column=1, sticky="w", padx=(0, 18))

ttk.Label(tracking_frame, textvariable=track_dec_s_var, font=value_font).grid(row=3, column=2, sticky="w", padx=(14, 3))
ttk.Label(tracking_frame, text="sec", font=font).grid(row=3, column=3, sticky="w")

# ------------------------------------------------------------------
# SOURCE OUTPUT
# ------------------------------------------------------------------
source_frame = ttk.LabelFrame(frame, text=" Source Coordinates ", padding=12)
source_frame.grid(row=current_row, column=0, columnspan=10, sticky="w", pady=(0, 0))
current_row += 1

ttk.Label(source_frame, text="RA", font=header_font).grid(row=0, column=0, sticky="w", padx=(14, 26))
ttk.Label(source_frame, text="Dec", font=header_font).grid(row=0, column=2, sticky="w", padx=(14, 0))

# Source StringVars
src_ra_h_var = tk.StringVar()
src_ra_m_var = tk.StringVar()
src_ra_s_var = tk.StringVar()

src_dec_d_var = tk.StringVar()
src_dec_m_var = tk.StringVar()
src_dec_s_var = tk.StringVar()

# Row 1
ttk.Label(source_frame, textvariable=src_ra_h_var, font=font).grid(row=1, column=0, sticky="w", padx=(14, 3))
ttk.Label(source_frame, text="hours", font=font).grid(row=1, column=1, sticky="w", padx=(0, 18))

ttk.Label(source_frame, textvariable=src_dec_d_var, font=font).grid(row=1, column=2, sticky="w", padx=(14, 3))
ttk.Label(source_frame, text="deg", font=font).grid(row=1, column=3, sticky="w")

# Row 2
ttk.Label(source_frame, textvariable=src_ra_m_var, font=font).grid(row=2, column=0, sticky="w", padx=(14, 3))
ttk.Label(source_frame, text="min", font=font).grid(row=2, column=1, sticky="w", padx=(0, 18))

ttk.Label(source_frame, textvariable=src_dec_m_var, font=font).grid(row=2, column=2, sticky="w", padx=(14, 3))
ttk.Label(source_frame, text="min", font=font).grid(row=2, column=3, sticky="w")

# Row 3
ttk.Label(source_frame, textvariable=src_ra_s_var, font=font).grid(row=3, column=0, sticky="w", padx=(14, 3))
ttk.Label(source_frame, text="sec", font=font).grid(row=3, column=1, sticky="w", padx=(0, 18))

ttk.Label(source_frame, textvariable=src_dec_s_var, font=font).grid(row=3, column=2, sticky="w", padx=(14, 3))
ttk.Label(source_frame, text="sec", font=font).grid(row=3, column=3, sticky="w")

# Consistent padding
for child in frame.winfo_children():
    child.grid_configure(padx=3, pady=3)

root.mainloop()
