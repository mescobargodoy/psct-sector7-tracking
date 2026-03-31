import astropy.units as u
from astropy.time import Time

from tracking_math import (
    compute_ra_dec_iteratively,
    get_named_source_coord,
    parse_manual_source,
    coord_to_table_strings,
)


# ------------------------------------------------------------------
# CLI helpers
# ------------------------------------------------------------------
def ask_nonempty(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Please enter a value.")


def ask_float(prompt):
    while True:
        value = input(prompt).strip()
        try:
            return float(value)
        except ValueError:
            print("Please enter a valid number.")


def ask_source_choice():
    print("\nSelect a source from the list below:")
    print("  1) none    (choose this if you want to input coordinates manually)")
    print("  2) crab")
    print("  3) mrk421")
    print("  4) mrk501")

    valid_map = {
        "1": "none",
        "2": "crab",
        "3": "mrk421",
        "4": "mrk501",
        "none": "none",
        "crab": "crab",
        "mrk421": "mrk421",
        "mrk501": "mrk501",
    }

    while True:
        choice = input("\nEnter source choice (number or name): ").strip().lower()
        if choice in valid_map:
            return valid_map[choice]
        print("Invalid choice. Please enter one of: 1, 2, 3, 4, none, crab, mrk421, mrk501")


def ask_manual_source():
    print("\nManual coordinate input selected.")
    print("Choose coordinate format:")
    print("  1) RA in h/m/s and Dec in d/m/s")
    print("  2) RA in degrees and Dec in degrees")

    while True:
        fmt = input("\nEnter format (1 or 2): ").strip()

        if fmt == "1":
            print("\nEnter RA in h/m/s and Dec in d/m/s:")
            ra_h = input("  RA hours: ").strip()
            ra_m = input("  RA min   [default 0]: ").strip()
            ra_s = input("  RA sec   [default 0]: ").strip()

            dec_d = input("  Dec deg  (negative allowed): ").strip()
            dec_m = input("  Dec min  [default 0]: ").strip()
            dec_s = input("  Dec sec  [default 0]: ").strip()

            return parse_manual_source(
                ra_h_text=ra_h,
                ra_m_text=ra_m,
                ra_s_text=ra_s,
                dec_d_text=dec_d,
                dec_m_text=dec_m,
                dec_s_text=dec_s,
            )

        elif fmt == "2":
            print("\nEnter RA/Dec in degrees:")
            ra_deg = input("  RA deg : ").strip()
            dec_deg = input("  Dec deg: ").strip()

            return parse_manual_source(
                ra_deg_text=ra_deg,
                dec_deg_text=dec_deg,
            )

        else:
            print("Invalid choice. Please enter 1 or 2.")


def ask_observation_time():
    utc_date = Time.now().utc.isot.split("T")[0]
    default_utc_time = Time.now().utc.isot.split("T")[1].split(".")[0]

    print(f"\nRun Start date is assumed to be today's UTC date: {utc_date}")
    print(f"Enter time in UTC format hh:mm:ss")
    print(f"Press Enter to use current UTC time: {default_utc_time}")

    time_str = input("Run Start (UTC hh:mm:ss): ").strip()
    if not time_str:
        time_str = default_utc_time

    observation_time = f"{utc_date}T{time_str}"
    return observation_time


def ask_run_length():
    print("\nEnter observing run length in minutes.")
    while True:
        value = input("Run Length (min) [default 20]: ").strip()
        if value == "":
            return 20.0 * u.min
        try:
            return float(value) * u.min
        except ValueError:
            print("Please enter a valid number.")


def print_coord_box(title, coord):
    parts = coord_to_table_strings(coord)

    width = 45
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)
    print(f"{'':4}{'RA':<18}{'Dec':<18}")
    print(f"{parts['ra_h']:<6} {'hours':<10} {parts['dec_d']:<6} {'deg':<10}")
    print(f"{parts['ra_m']:<6} {'min':<10} {parts['dec_m']:<6} {'min':<10}")
    print(f"{parts['ra_s']:<6} {'sec':<10} {parts['dec_s']:<6} {'sec':<10}")
    print("=" * width)


# ------------------------------------------------------------------
# Main CLI program
# ------------------------------------------------------------------
def main():
    print("=" * 55)
    print("pSCT Sector7 Tracking Calculator (CLI)".center(55))
    print("=" * 55)

    try:
        source_choice = ask_source_choice()

        if source_choice == "none":
            source_coord = ask_manual_source()
        else:
            source_coord = get_named_source_coord(source_choice)

        observation_time = ask_observation_time()
        duration = ask_run_length()

        print("\nComputing pointing...")

        tracking_coord = compute_ra_dec_iteratively(
            observation_time=observation_time,
            observation_run_length=duration,
            source_coord=source_coord,
        )

        print_coord_box("Tracking Coordinates", tracking_coord)
        print_coord_box("Source Coordinates", source_coord)

    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
