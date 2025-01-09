#!/usr/bin/env python

"""
Show a timer in the command line and upon completion of a period duration show a
popup.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
import time
import tkinter
import tkinter.messagebox
from typing import NamedTuple

HOURS_RE = re.compile(r"^(\d+)h(?:ours)?$")
MINUTES_RE = re.compile(r"^(\d+)m(?:in(?:utes)?)?$")
SECONDS_RE = re.compile(r"^(\d+)s(?:ec(?:onds)?)?$")


class _Arguments(NamedTuple):
    period_durations: list[datetime.timedelta]
    min_more_time: datetime.timedelta


def _interpret_period_duration_argument(argument: str) -> datetime.timedelta:
    if (hours_match := HOURS_RE.match(argument)) is not None:
        return datetime.timedelta(hours=int(hours_match.group(1)))
    if (minutes_match := MINUTES_RE.match(argument)) is not None:
        return datetime.timedelta(minutes=int(minutes_match.group(1)))
    if (seconds_match := SECONDS_RE.match(argument)) is not None:
        return datetime.timedelta(seconds=int(seconds_match.group(1)))
    raise ValueError(f"Unable to interpret {argument} (use one of {HOURS_RE}, {MINUTES_RE}, {SECONDS_RE}).")


def _interpret_period_duration_arguments(argument: str) -> list[datetime.timedelta]:
    return [_interpret_period_duration_argument(arg) for arg in argument.split(",")]


def _parse_arguments() -> _Arguments:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d",
        "--period-durations",
        type=str,
        default="25min,5min",
        help="Period durations as comma-separated string, use 'h'/'hours',"
        " 'min'/'minutes', 's'/'sec'/'seconds' to deonote the unit, defaults to"
        " %(default)s.",
    )
    parser.add_argument(
        "--min-more-time",
        default="1min",
        help="Minimal amount of time to give the user after a timer has elapsed; defaults to %(default)s.",
    )
    args = parser.parse_args()
    return _Arguments(
        period_durations=_interpret_period_duration_arguments(args.period_durations),
        min_more_time=_interpret_period_duration_argument(args.min_more_time),
    )


def _round_to_nearest_second(t: datetime.timedelta) -> datetime.timedelta:
    return datetime.timedelta(seconds=round((t + datetime.timedelta(seconds=0.5)).total_seconds()))


ZERO = datetime.timedelta(seconds=0)


class _PrintMetaInfo(NamedTuple):
    period_counter: int
    period_duration: datetime.timedelta
    is_overtime: bool = False

    def with_is_overtime(self) -> _PrintMetaInfo:
        return _PrintMetaInfo(
            period_counter=self.period_counter,
            period_duration=self.period_duration,
            is_overtime=True,
        )


def _sleep_for(period_duration: datetime.timedelta, print_info: _PrintMetaInfo) -> None:
    period_start = datetime.datetime.now()
    sys.stdout.write("\033[K")  # clear line
    while (time_remaining := (period_duration - (datetime.datetime.now() - period_start))) > ZERO:
        if not print_info.is_overtime:
            print(
                f"period {print_info.period_counter: >3}:",
                _round_to_nearest_second(time_remaining),
                "of",
                print_info.period_duration,
                end="\r",
            )
        else:
            print(
                f"period {print_info.period_counter: >3}:",
                print_info.period_duration,
                "+",
                _round_to_nearest_second(time_remaining),
                "overtime",
                "of",
                print_info.period_duration,
                end="\r",
            )
        time.sleep(1)
    return


_MIN_MORE_TIME = datetime.timedelta(seconds=60)


def _more_time(period_duration: datetime.timedelta) -> datetime.timedelta:
    return max(_MIN_MORE_TIME, _round_to_nearest_second(period_duration / 10))


def _ask_user_to_continue(print_info: _PrintMetaInfo) -> None:
    # disable the 'root' window of tk
    root = tkinter.Tk()
    root.withdraw()

    while (
        tkinter.messagebox.askokcancel(
            title="Timer elapsed",
            message=(
                f"Timer {print_info.period_counter} elapsed after {print_info.period_duration}."
                " Continue to the next timer?"
                f" If not, we'll give you {_more_time(print_info.period_duration)} more time."
            ),
        )
        is False
    ):
        root.update()  # ensure popup is closed after button click
        period_duration = _more_time(print_info.period_duration)
        _sleep_for(period_duration, print_info.with_is_overtime())
    root.update()  # ensure popup is closed after button click


def main() -> None:
    arguments = _parse_arguments()
    print("Period durations are", ", ".join(str(d) for d in arguments.period_durations))
    global _MIN_MORE_TIME
    _MIN_MORE_TIME = arguments.min_more_time

    period_counter = 0
    while True:
        period_index = period_counter % len(arguments.period_durations)
        period_duration = arguments.period_durations[period_index]
        print_info = _PrintMetaInfo(period_counter, period_duration)
        _sleep_for(period_duration, print_info)
        _ask_user_to_continue(print_info)
        period_counter += 1


if __name__ == "__main__":
    main()
