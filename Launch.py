import threading
from datetime import datetime, timezone, tzinfo
from datetime import timedelta
from datetime import timezone as tzone
import time
import pandas as pd
import numpy as np
import string
import random
import uuid
import os
import calendar


class Scheduler:
    """
    A class to represent a schedule for jobs with start and end dates.

    Attributes:
    -----------
    threading : boolean
        Whether or not to use threading while running the jobs

    Methods:
    --------
    job():
        Method to create and configure a job
    run_all():
        Runs all jobs with or without threading
    """

    def __init__(self, threading=False, start_date=None, time_zone=None):

        # ensuring that we get appropriate type of parameters for Scheduler
        if not isinstance(time_zone, int) and time_zone is not None:
            raise ValueError("Timezone must be an integer")

        if not isinstance(start_date, str) and start_date is not None:
            raise ValueError("Date must be an str format %Y-%m-%d %H:%M")

        self.threads = threading   #threading
        # start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M')

        # Parse start_date or default to the current datetime object
        self.start_date = (
            datetime.strptime(start_date, '%Y-%m-%d %H:%M')
            if start_date
            else datetime.now().replace(second=0)  # This is a datetime object
        )
        self.raw_start_date = self.start_date

        # print(self.start_date)


        # timezone of scheduler
        # Scheduler's timezone (default to current system timezone if not provided)
        self.scheduler_timezone = (
            tzone(timedelta(hours=time_zone))
            if time_zone is not None
            else datetime.now().astimezone().tzinfo
        )

        # Determine the local timezone
        self.local_timezone = datetime.now().astimezone().tzinfo
        # print(f'FUCKING LOCAL TIMEZONE {self.local_timezone}')

        # Parse and convert start_date to local timezone if needed
        if self.start_date:
            # Parse start_date in the passed timezone
            passed_timezone = self.scheduler_timezone

            # uncorvensioned start_date (Passed startdate)
            self.passed_start_date = self.start_date.replace(tzinfo=passed_timezone)

            # convert to local timezone if different
            if passed_timezone != self.local_timezone:
                # print(f'I AM IN NOT EQUAL')
                self.scheduler_startdate = self.passed_start_date.astimezone(self.local_timezone)
            else:
                self.scheduler_startdate = self.passed_start_date
        else:
            # default to current time in the local timezone
            self.scheduler_startdate = datetime.now().replace(microsecond=0).astimezone(self.local_timezone)

        # print(f"this is scheduler startdate and timezone inside scheduler class:\n {self.scheduler_timezone}\n{self.scheduler_startdate}\n")

        # validating that passed starting date isn't more than current time
        if self.scheduler_startdate.strftime('%Y-%m-%d %H:%M') < datetime.now().strftime('%Y-%m-%d %H:%M'):
            raise ValueError("Start date cannot be less than the current date")


        # empty list for adding jobs later
        self.jobs = []


    def job(self, start_date=None, time_zone=None):

        """
        Creates and configures a job with a specified start date and time zone.

        Args:
        -----
        startdate : str, optional
            The start date of the job in the format '%Y-%m-%d %H:%M'. If not provided, the scheduler's default start date is used.

        timezone : int, optional
            The timezone offset in hours. If not provided, the scheduler's default timezone is used.

        Raises:
        -------
        ValueError
            If the timezone is not an integer or if the start date is not in the correct string format.
            If the job start date is set to a time earlier than the current date and time.

        Returns:
        --------
        JobWrapper
            A JobWrapper object that allows further configuration of the job.
        """

        # ensuring that we get appropriate type of parameters for job
        if not isinstance(time_zone, int) and time_zone is not None:
            raise ValueError("Timezone must be an integer")

        if not isinstance(start_date, str) and start_date is not None:
            raise ValueError("Date must be an str fromat %Y-%m-%d %H:%M")

        job_timezone = (
            tzone(timedelta(hours=time_zone))
            if time_zone is not None
            else self.scheduler_timezone
        )
        # print(f'this is job timezone {job_timezone}')

        # determine the local timezone
        local_timezone = datetime.now().astimezone().tzinfo

        # Parse start_date or default to the current datetime object
        self.start_date = (
            datetime.strptime(start_date, '%Y-%m-%d %H:%M')
            if start_date
            else self.raw_start_date # This is a datetime object
        )


        # Parse and convert the job start date
        if self.start_date:
            # Assign the provided timezone to the start_date
            self.start_date_with_tz = self.start_date.replace(tzinfo=job_timezone)
            # If the job's timezone is different from the local timezone, convert it
            if job_timezone != local_timezone:
                job_startdate = self.start_date_with_tz.astimezone(local_timezone)
            else:
                job_startdate = self.start_date_with_tz
        else:
            if job_timezone != local_timezone:
                job_startdate = self.passed_start_date.astimezone(local_timezone)
            else:
                job_startdate = self.start_date_with_tz

        # print(f"this is job startdate and timezone inside job function: \n{job_timezone}\n{job_startdate}\n")

        # ensuring that start date isn't in the past
        if job_startdate.strftime('%Y-%m-%d %H:%M') < datetime.now().strftime('%Y-%m-%d %H:%M'):
            raise ValueError("Job start date cannot be less than the current date")

        # creating the job configuration as a dictionary with default values for job parameters
        job = {
            'startdate': job_startdate,
            'time_zone': job_timezone,
            'end_date': None,
            'func': None,
            'name': None,
            'unit': None,
            'interval': None,
            'next_run': None,
            'repeats': None,  # New attribute for repeats
            'repeat_count': 0,  # Counter for completed runs
            'args': (),
            'kwargs': {}
        }


        # encapsulation of job configuration
        class JobWrapper:
            """
            A wrapper class to represent an individual job within the scheduler.

            Attributes:
            -----------
            job : dict
                Dictionary containing configuration parameters of the job.

            Methods:
            --------
            second(every=1):
                Sets the job to run every specified number of seconds. (code runs in every 1 second as default)
            minute(every=1):
                Sets the job to run every specified number of minutes. (code runs in every 1 minute as default)
            hour(every=1):
                Sets the job to run every specified number of hours. (code runs in every 1 hour as default)
            day(every=1, hour=None):
                Sets the job to run every specified number of days at an optional specific time. (code runs in every 1 day as default)
            week(every=1, week_day=None, hour=None):
                Sets the job to run every specified number of weeks on specified weekdays and time. (code runs in every 1 week as default)
            do(func, name):
                Configures the function to run with the job and assigns a name to the job.
            until(end date):
                Sets the end date for the job.
            repeat(times):
                Sets the number of times the job should repeat.
            calculate_next_run(current_time):
                Calculates the next run time of the job based on its schedule.
            run(*args, **kwargs):
                Executes the job at its scheduled times with the provided arguments.
            """

            def __init__(self, job):
                self.job = job  # passes the job that should get executed


            def second(self, every=1):
                """
                Sets the job to run every `every` seconds and defines unit as a second

                Args:
                -----
                every : Sets the job to run every specified number of seconds.
                """

                if every is not None and isinstance(every, str):
                    raise ValueError("Passed argument must be a positive integer")
                if every is not None and every<0:
                    raise ValueError("Passed argument must be a positive integer")

                self.job['unit'] = 'second'  # time unit for the job
                self.job['interval'] = every # interval
                return self

            def minute(self, every=1):
                """Set the job to run every `every` minutes."""

                if every is not None and isinstance(every, str):
                    raise ValueError("Passed argument must be a positive integer")
                if every is not None and every<0:
                    raise ValueError("Passed argument must be a positive integer")
                self.job['unit'] = 'minute'
                self.job['interval'] = every
                return self

            def hour(self, every=1):
                """Set the job to run every `every` hours."""

                if every is not None and isinstance(every, str):
                    raise ValueError("Passed argument must be a positive integer")
                if every is not None and every<0:
                    raise ValueError("Passed argument must be a positive integer")

                self.job['unit'] = 'hour'
                self.job['interval'] = every
                return self

            def day(self, every=1, hour=None):
                """Set the job to run every `every` days, optionally at a specific time."""

                if every is not None and isinstance(every, str):
                    raise ValueError("Passed argument must be a positive integer")
                if every is not None and every<0:
                    raise ValueError("Passed argument must be a positive integer")

                self.job['unit'] = 'day'
                self.job['interval'] = every
                self.job['at'] = hour
                return self

            def week(self, every=1, week_day=None, hour=None):
                """
                Set the job to run every `every` weeks on specific weekdays at a specific time.
                If `week_day` is None, the job will every week.

                Parameters:
                -----------
                every : int
                    Interval in weeks.
                week_day : int, list of int, or None
                    Single integer or list of weekdays where 0 = Monday, ..., 6 = Sunday. If None, run every day.
                hour : str
                    Time in HH:MM format at which the job should run.
                """

                if every is not None and isinstance(every, str):
                    raise ValueError("Passed argument must be a positive integer")
                if every is not None and every<0:
                    raise ValueError("Passed argument must be a positive integer")

                if  week_day and  type(week_day) != int and type(week_day)!=list:
                    raise ValueError("Weekday must be an integer or a list of integers")
                elif week_day and isinstance(week_day, list):
                    # Check if all elements are integers
                    if not all(isinstance(i, int) for i in week_day):
                        raise ValueError('List of Weekdays must contain integers only')

                    # Check if the list length is more than 6
                    if len(week_day) > 6:
                        raise ValueError('List of Weekdays cannot contain more than 6 items')

                    # Check if each number in the list is between 0 and 6
                    if not all(0 <= i <= 6 for i in week_day):
                        raise ValueError('Each Weekday number must be between 0 and 6')
                elif week_day and type(week_day)==int and week_day>6:
                    raise ValueError('Weekday is Specified to be between 0 and 6')

                self.job['unit'] = 'week'
                self.job['interval'] = every

                # passed week days are saved in list then turned into sets to avoid repeating values without raising errror
                # then sets are once again turned into lists
                self.job['week_day'] = [datetime.today().weekday()] if week_day is None else [week_day] if isinstance(week_day, int) else list(set(week_day))
                # print( self.job['week_day'])
                # defining at what hour of the day code should run
                self.job['at'] = hour
                return self

            def month(self, every=1, day=None, hour=None):
                """
                Set the job to run every `every` months, optionally on a specific day and time.

                Parameters:
                -----------
                every : int
                    Interval in months.
                day : int or None
                    Day of the month to run the job. If None, uses the current day.
                hour : str
                    Time in HH:MM format at which the job should run.
                """

                if every is not None and isinstance(every, str):
                    raise ValueError("Passed argument must be a positive integer")
                if every is not None and every<0:
                    raise ValueError("Passed argument must be a positive integer")

                self.job['unit'] = 'month'
                self.job['interval'] = every
                self.job['on_day'] = day
                self.job['at'] = hour
                return self

            def year(self, every=1, month=None, day=None, hour=None):
                """
                Set the job to run every `every` years, optionally on a specific month, day, and time.

                Parameters:
                -----------
                every : int
                    Interval in years.
                month : int or None
                    Month of the year to run the job (1-12). If None, uses the current month.
                day : int or None
                    Day of the month to run the job. If None, uses the current day.
                hour : str
                    Time in HH:MM format at which the job should run.
                """

                if every is not None and isinstance(every, str):
                    raise ValueError("Passed argument must be a positive integer")
                if every is not None and every<0:
                    raise ValueError("Passed argument must be a positive integer")

                self.job['unit'] = 'year'
                self.job['interval'] = every
                self.job['on_month'] = month
                self.job['on_day'] = day
                self.job['at'] = hour
                return self

            def do(self, func, name):
                self.job['func'] = func
                self.job['name'] = name
                return self


            def until(self, end_date):
                # Validate time_zone and determine the timezone to use for the end_date
                end_timezone = self.job['time_zone']  # Default to the job's timezone
                end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M')

                # Determine the local timezone
                local_timezone = datetime.now().astimezone().tzinfo

                # Parse and assign timezone to the end_date
                end_date_with_tz = end_date.replace(tzinfo=end_timezone)

                # Convert to local timezone if the end_date's timezone differs
                if end_timezone != local_timezone:
                    end_date_local = end_date_with_tz.astimezone(local_timezone)
                else:
                    end_date_local = end_date_with_tz

                # print(f"This is the job's timezone and the converted end date in 'until':\n{self.job['time_zone']}\n{end_date_local}\n")

                # Ensure the end_date is not earlier than the job's start_date
                if end_date_local < self.job['startdate']:
                    raise ValueError('End date must be later than the start date.')

                # Assign the converted end_date to the job
                self.job['end_date'] = end_date_local

                # print(f"this is job timezone abd end date in untill:\n {self.job['time_zone']}\n { self.job['end_date']}\n")
                return self


            def repeat(self, times):
                """Set the number of times the job should repeat."""
                self.job['repeats'] = times
                return self

            def calculate_next_run(self, current_time):
                # Truncate the current_time to remove milliseconds
                current_time = current_time.replace(microsecond=0)

                if self.job['unit'] == 'second':
                    self.job['next_run'] = current_time + timedelta(seconds=self.job['interval'])
                elif self.job['unit'] == 'minute':
                    current_time = current_time.replace(second=0)
                    self.job['next_run'] = current_time + timedelta(minutes=self.job['interval'])
                elif self.job['unit'] == 'hour':
                    current_time = current_time.replace(minute=0, second=0)
                    self.job['next_run'] = current_time + timedelta(hours=self.job['interval'])
                elif self.job['unit'] == 'day':
                    # Handling the 'at' parameter for the day interval
                    if 'at' in self.job and self.job['at']:
                        # Parse the 'at' time from the job settings
                        hour, minute = map(int, self.job['at'].split(':'))
                        next_run = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

                        # Ensure next_run is set on the correct day interval
                        if next_run <= current_time:
                            next_run += timedelta(days=self.job['interval'])
                        self.job['next_run'] = next_run
                    else:
                        # Default behavior without 'at' attribute
                        current_time = current_time.replace(hour=0, minute=0, second=0)
                        self.job['next_run'] = current_time + timedelta(days=self.job['interval'])
                elif self.job['unit'] == 'week':
                    # Set up the initial next run time based on the current time and interval
                    runlist = []
                    next_run = current_time + timedelta(weeks=self.job['interval'])
                    print(f'Added next run{next_run.weekday()}')
                    # Default to current weekday if no week_day is specified
                    weekdays = self.job['week_day'] if self.job['week_day'] else [current_time.weekday()]
                    for day in weekdays:
                        print( current_time.weekday(),day)
                        days_difference = current_time.weekday() - day
                        next_run = next_run - timedelta(days=days_difference)
                        print(next_run)

                        if 'at' in self.job and self.job['at']:
                            hour, minute = map(int, self.job['at'].split(':'))
                            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)

                        # If the next run time is in the past, add the weekly interval
                        if next_run <= current_time:
                            next_run += timedelta(weeks=self.job['interval'])

                        runlist.append(next_run)
                        next_run = current_time + timedelta(weeks=self.job['interval'])

                    self.job['next_run'] = min(runlist)
                elif self.job['unit'] == 'month':
                    # Handle the 'on_day' parameter
                    day = self.job.get('on_day') or current_time.day
                    # Handle 'at' parameter
                    if 'at' in self.job and self.job['at']:
                        hour, minute = map(int, self.job['at'].split(':'))
                    else:
                        hour, minute = current_time.hour, current_time.minute

                    # Calculate next month and year
                    total_months = current_time.month - 1 + self.job['interval']
                    next_year = current_time.year + total_months // 12
                    next_month = total_months % 12 + 1

                    try:
                        next_run = current_time.replace(year=next_year, month=next_month, day=day, hour=hour, minute=minute, second=0)
                    except ValueError:
                        # Adjust for invalid day of month
                        last_day = calendar.monthrange(next_year, next_month)[1]
                        next_run = current_time.replace(year=next_year, month=next_month, day=last_day, hour=hour, minute=minute, second=0)
                    if next_run <= current_time:
                        # Increment month
                        total_months += self.job['interval']
                        next_year = current_time.year + total_months // 12
                        next_month = total_months % 12 + 1
                        try:
                            next_run = current_time.replace(year=next_year, month=next_month, day=day, hour=hour, minute=minute, second=0)
                        except ValueError:
                            last_day = calendar.monthrange(next_year, next_month)[1]
                            next_run = current_time.replace(year=next_year, month=next_month, day=last_day, hour=hour, minute=minute, second=0)

                    self.job['next_run'] = next_run
                elif  self.job['unit'] == 'year':
                    month = self.job.get('on_month') or current_time.month
                    day = self.job.get('on_day') or current_time.day
                    if 'at' in self.job and self.job['at']:
                        hour, minute = map(int, self.job['at'].split(':'))
                    else:
                        hour, minute = current_time.hour, current_time.minute

                    next_year = current_time.year + self.job['interval']
                    try:
                        next_run = current_time.replace(year=next_year, month=month, day=day, hour=hour, minute=minute, second=0)
                    except ValueError:
                        last_day = calendar.monthrange(next_year, month)[1]
                        next_run = current_time.replace(year=next_year, month=month, day=last_day, hour=hour, minute=minute, second=0)

                    if next_run <= current_time:
                        next_year += self.job['interval']
                        try:
                            next_run = current_time.replace(year=next_year, month=month, day=day, hour=hour, minute=minute, second=0)
                        except ValueError:
                            last_day = calendar.monthrange(next_year, month)[1]
                            next_run = current_time.replace(year=next_year, month=month, day=last_day, hour=hour, minute=minute, second=0)

                    self.job['next_run'] = next_run
                else:
                    raise ValueError("Unsupported unit. Please extend the `calculate_next_run` method to support other units.")
                # print(f"calc next run: {self.job['next_run']}")

                return self.job['next_run']


            def run(self, *args, **kwargs):
                # Wait until jstartdate occurs
                now = datetime.now().replace(microsecond=0)

                # print(f"this is when startdate should be:\n{self.job['startdate'].replace(tzinfo=None)}\nand this is now:\n{now}\n")
                if now < self.job['startdate'].replace(tzinfo=None):
                    wait_time = (self.job['startdate'].replace(tzinfo=None) - now).total_seconds()
                    # print(f"waiting for {wait_time}")
                    time.sleep(wait_time)

                # Check if end date is today and at time is in the past
                if self.job['end_date'] and self.job['end_date'].date() == now.date() and 'at' in self.job and self.job['at']:
                    hour, minute = map(int, self.job['at'].split(':'))
                    at_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if at_time < now.replace(second=0, microsecond=0):
                        raise ValueError("The specified hour is earlier than the current time for today's end date.")

                while True:
                    # defining now 1st time so we can run the function at the very first place
                    now = datetime.now().astimezone().replace(microsecond=0)
                    # print(f"----------------\nnow in while is: {now}\n")

                    # ensuring that code runs for the first time or at the time that it has to run next
                    if self.job['next_run'] is None or now >= self.job['next_run']:
                        # if code reaches it's upper limit time it stops running
                        if self.job['end_date'] and now.replace(second=0,microsecond=0) >= self.job['end_date']:
                            print(self.job['end_date'], now.replace(second=0,microsecond=0))
                            print('in first break')
                            break

                        # ensuring there is function to run
                        if self.job['func']:
                            try:
                                # trying to run a function that was passed to a job
                                # and after finish running calculating its next run ime
                                self.job['func'](*self.job['args'], **self.job['kwargs'])  # Run the job

                                # after running the function we should add repeats method a value
                                # to ensure it repeats as many times as we passed it.
                                self.job['repeat_count'] += 1

                                # calculating next run
                                self.calculate_next_run(now)

                            # if function fails to run then it goes to exception block and
                            # still calculates the next run time
                            except Exception as e:
                                print(f"Job {self.job['name']} failed with exception: {e}")
                                self.calculate_next_run(now)


                            # handles important termination conditions for the job,
                            # ensuring it stops executing under specific circumstances
                            finally:
                                # self.job['repeat_count'] += 1
                                now = datetime.now().astimezone().replace(microsecond=0)
                                # print(f'final calcnexttrun')
                                next_run_time = self.calculate_next_run(now)

                                if self.job['end_date'] and next_run_time > self.job['end_date']:
                                    print('BREAK CUZ NEXT RUN IS AFTER UNTIL')
                                    break

                                    # if code reaches it's upper limit time it stops running
                                if self.job['end_date'] and now.replace(second=0,microsecond=0) >= self.job['end_date']:
                                    print(self.job['end_date'], now.replace(second=0,microsecond=0))
                                    print('in mid break')
                                    break

                                if self.job['repeats'] is not None and self.job['end_date'] is None and self.job['repeat_count'] >= self.job['repeats']:
                                    # print(self.job['repeat_count'])
                                    # print('repeatbreak?')
                                    break

                            # overwriting on now variable so we can define it as the time when function ends running /
                            # this ensures that all subsequent calculations (like determining whether the job should
                            # continue running or checking the next run time) use the latest execution time
                            # as a reference point.
                            now = datetime.now().astimezone().replace(microsecond=0)

                    # ensures the job doesn't run past its scheduled end time.
                    # even if the job has a repeating schedule (e.g., every minute or every hour),
                    # this condition guarantees that no new runs will be initiated once the end_date is reached.
                    if self.job['end_date'] and now >= self.job['end_date']:
                        print('in second break')
                        break


        job_wrapper = JobWrapper(job)
        self.jobs.append(job_wrapper)
        return job_wrapper

    def run_all(self):
        if self.threads:
            threads = []
            for job in self.jobs:
                thread = threading.Thread(target=job.run)
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()
        else:
            for job in self.jobs:
                job.run()


