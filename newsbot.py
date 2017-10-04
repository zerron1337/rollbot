import discord
import time
import calendar
import asyncio
import os.path
import json
import re
from enum import Enum

from datetime import datetime
from datetime import timedelta

subscribers_file = 'newsbot_subs.json'
events = []

command_key = '!'
test_token = ''
prod_token = ''
client = discord.Client()
help_message = """
`Available commands:`

**!sub** *event* - bot will tag you on *event*
**!unsub** *event* - bot will stop tagging you on *event*

**!utc** - shows current time in UTC
**!remind** *[every]* *[[<weekday>] <time> | <number> days | hours | minutes]* *[note]* - bot will ping you when provided time comes
Examples:
!remind 1 hour some stuff happens
!remind every monday 15:30 more stuff happens
!remind saturday weekend!
!remind 18:00
!remind 2 days
**!reminders** - sends you the list of your active reminders
**!clear** - clears the list of your active reminders

Both commands will print events list if used without *event* argument (e.g. "!sub", "!unsub")
"""

notify_channel_id = '314049171332005891'

invasion_anchor = 1494372600
invasion_image_url = 'https://hydra-media.cursecdn.com/wow.gamepedia.com/thumb/9/95/ToS_Trailer_Legion_Ship2.png/300px-ToS_Trailer_Legion_Ship2.png'
invasion_timer_flag = False

reminders_file = 'newsbot_reminders.json'
reminders = {}
weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


class ReminderArgType(Enum):
    unknown = 0
    std_time = 1
    integer = 2
    weekday = 3
    hour_word = 4
    minute_word = 5
    day_word = 6
    recurring = 7


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    global reminders
    try:
        f = open(reminders_file)
        reminders = json.load(f)
        f.close()
    except:
        pass
    #asyncio.ensure_future(invasion_event())
    asyncio.ensure_future(reminder_event())


@client.event
async def on_message(message):
    if message.content.startswith(command_key + 'sub'):
        args = message.content.strip().split(' ')[1:]
        if len(args) < 1:
            await client.send_message(message.channel, get_events_list_msg(message.author.id))
            return
        subs_count = 0
        for arg in args:
            if arg in events and subscribe(arg, message.author.id):
                subs_count += 1
                await client.send_message(message.channel, '<@%s> subscribed to **%s**.' % (message.author.id, arg))
        if subs_count < 1:
            await client.send_message(message.channel, get_events_list_msg(message.author.id))
    elif message.content.startswith(command_key + 'unsub'):
        args = message.content.strip().split(' ')[1:]
        if len(args) < 1:
            await client.send_message(message.channel, get_events_list_msg(message.author.id))
            return
        unsubs_count = 0
        for arg in args:
            if arg in events and unsubscribe(arg, message.author.id):
                unsubs_count += 1
                await client.send_message(message.channel, '<@%s> unsubscribed from **%s**.' % (message.author.id, arg))
        if unsubs_count < 1:
            await client.send_message(message.channel, get_events_list_msg(message.author.id))
    elif message.content.startswith(command_key + 'utc'):
        await client.send_message(message.channel,
                                  datetime.utcfromtimestamp(int(time.time())).strftime('%A %#d %B %H:%M'))
    elif message.content.startswith(command_key + 'reminders'):
        reminders_list = ''
        if message.author.id in reminders:
            for entry in reminders[message.author.id]:
                dt = datetime.utcfromtimestamp(entry['remind_date'])
                str = dt.strftime('%A %#d %B %H:%M')
                if len(entry['note']) > 0:
                    str += ' - "%s"' % entry['note']
                if entry['is_recurring'] == 1:
                    str += ' - repeats every %s' % seconds_to_str(entry['recur_period'])
                reminders_list += '%s\n' % str
        if len(reminders_list) > 0:
            await client.send_message(message.author, 'Active reminders:\n%s' % reminders_list)
            await client.send_message(message.channel,
                                      'Sent list of active reminders to you, <@%s>.' % message.author.id)
        else:
            await client.send_message(message.channel,
                                      'You don\'t have any active reminders, <@%s>.' % message.author.id)
    elif message.content.startswith(command_key + 'remind'):
        args = message.content.strip().split(' ')[1:]
        now = datetime.utcnow()
        remind_date = now.replace(second=0)
        recur_period = 0
        is_recurring = False
        note = ''
        i = 0
        if len(args) > i:
            arg_type = get_remind_arg_type(args[i])
            if arg_type is ReminderArgType.recurring:
                is_recurring = True
                i += 1
            if len(args) > i:
                arg_type = get_remind_arg_type(args[i])
                if arg_type is ReminderArgType.weekday:
                    weekday_code = day_code(args[i])
                    recur_period = 24 * 60 * 60 * 7
                    remind_date += timedelta(
                        days=(weekday_code - now.weekday()) if now.weekday() < weekday_code else (
                            7 - now.weekday() + weekday_code))
                    i += 1
                    if len(args) > i:
                        arg_type = get_remind_arg_type(args[i])
                        if arg_type is ReminderArgType.std_time:
                            match = re.search(r'^(([01]?\d)|(2[0-3])+):([0-5]\d)$', args[i])
                            if match:
                                hours = int(match.group(1))
                                minutes = int(match.group(4))
                                remind_date = remind_date.replace(hour=hours, minute=minutes)
                                i += 1
                elif arg_type is ReminderArgType.integer:
                    n = int(args[i])
                    i += 1
                    if len(args) > i:
                        arg_type = get_remind_arg_type(args[i])
                        if arg_type is ReminderArgType.day_word:
                            remind_date += timedelta(days=n)
                            recur_period = n * 24 * 60 * 60
                            i += 1
                        elif arg_type is ReminderArgType.hour_word:
                            remind_date += timedelta(hours=n)
                            recur_period = n * 60 * 60
                            i += 1
                        elif arg_type is ReminderArgType.minute_word:
                            remind_date += timedelta(minutes=n)
                            recur_period = n * 60
                            i += 1
                elif arg_type is ReminderArgType.std_time:
                    match = re.search(r'^(([01]?\d)|(2[0-3])+):([0-5]\d)$', args[i])
                    if match:
                        hours = int(match.group(1))
                        minutes = int(match.group(4))
                        remind_date = remind_date.replace(hour=hours, minute=minutes)
                        if remind_date < now:
                            remind_date += timedelta(days=1)
                        recur_period = 24 * 60 * 60
                        i += 1
            if remind_date > now:
                if len(args) > i:
                    note = ' '.join(args[i:])
                if message.author.id not in reminders:
                    reminders[message.author.id] = []
                reminders[message.author.id].append({
                    'remind_date': calendar.timegm(remind_date.timetuple()),
                    'recur_period': recur_period,
                    'is_recurring': 1 if is_recurring else 0,
                    'note': note
                })
                f = open(reminders_file, 'w')
                json.dump(reminders, f, indent=4)
                f.close()
                await client.send_message(message.channel, 'Reminder added, <@%s>. I\'ll ping you when time comes.' % message.author.id)
                return
        await client.send_message(message.channel, 'Invalid command format, <@%s>. Try %shelp or %scommands.' % (
            message.author.id, command_key, command_key))
    elif message.content.startswith(command_key + 'clear'):
        reminders[message.author.id] = []
        f = open(reminders_file, 'w')
        json.dump(reminders, f, indent=4)
        f.close()
        await client.send_message(message.channel, 'Cleared all your active reminders, <@%s>.' % message.author.id)
    elif message.content.startswith(command_key + 'help') or message.content.startswith(command_key + 'commands'):
        await client.send_message(message.author, help_message)
        await client.send_message(message.channel, 'Sent commands description to you, <@%s>.' % message.author.id)
    elif message.author.id == client.user.id and message.content.startswith('```md'):
        if is_legit_dubs(message.content):
            await tag_subscribers(message.channel, 'dubs', False)


def get_events_list_msg(user_id):
    str = "<@%s>, available events to subscribe to:\n" % user_id
    subs = get_subs()
    for event in events:
        str += ' - %s' % event
        try:
            str += " (**subscribed**)\n" if user_id in subs[event] else "\n"
        except KeyError:
            pass
    return str


def seconds_before_invasion():
    timestamp = int(time.time())
    delta = 18 * 3600 + 30 * 60
    return delta - (timestamp - invasion_anchor) % delta


def next_invasion_dates(count=10):
    timestamp = int(time.time())
    next_in = seconds_before_invasion()
    delta = 18 * 3600 + 30 * 60
    next_date = timestamp + next_in
    next_date_end = timestamp + next_in + 6 * 3600
    realm_tz = 2 * 3600
    dates = [datetime.utcfromtimestamp(next_date + realm_tz).strftime('%A %#d %B %H:%M - ') + datetime.utcfromtimestamp(
        next_date_end + realm_tz).strftime('%H:%M')]
    for i in range(1, count):
        dates.append(datetime.utcfromtimestamp(next_date + realm_tz + delta * i).strftime(
            '%A %#d %B %H:%M - ') + datetime.utcfromtimestamp(next_date_end + realm_tz + delta * i).strftime('%H:%M'))
    return dates


async def invasion_event():
    global invasion_timer_flag
    if invasion_timer_flag:
        return

    invasion_timer_flag = True
    await asyncio.sleep(seconds_before_invasion() + 1)
    invasion_timer_flag = False

    channel = client.get_channel(notify_channel_id)
    if channel is None:
        channel = next(iter(client.servers))
    em = discord.Embed(description='Legion invasion is active **now** on EU servers!', colour=0x237f52)
    em.set_author(name='Broken Isles Invasion', icon_url=client.user.avatar_url)
    em.set_image(url=invasion_image_url)
    await client.send_message(channel, embed=em)
    await tag_subscribers(channel, 'invasions')
    await asyncio.sleep(6 * 3600)
    end_msg = "Legion invasion ended on EU servers.\nNext invasions (realm time):\n"
    inv_dates = next_invasion_dates()
    for inv_date in inv_dates:
        end_msg += "%s\n" % inv_date
    em = discord.Embed(description=end_msg, colour=0x237f52)
    em.set_author(name='Broken Isles Invasion', icon_url=client.user.avatar_url)
    em.set_image(url=invasion_image_url)
    await client.send_message(channel, embed=em)

    asyncio.ensure_future(invasion_event())


async def reminder_event():
    await asyncio.sleep(30)

    timestamp = int(time.time())
    for user_id, entries in reminders.items():
        for i, entry in enumerate(entries):
            if entry['remind_date'] < timestamp:
                message = 'Just reminding you that time has come for "%s".' % entry['note'] if len(entry['note']) > 0 else 'You asked me to ping you before. It is time!'
                if entry['is_recurring'] == 1:
                    next_reminder = entry['remind_date'] + entry['recur_period']
                    while next_reminder < timestamp:
                        next_reminder += entry['recur_period']
                    dt = datetime.utcfromtimestamp(next_reminder)
                    message += '\nNext reminder on %s' % dt.strftime('%A %#d %B %H:%M')
                    reminders[user_id][i]['remind_date'] = next_reminder
                else:
                    reminders[user_id].remove(entry)
                user = await client.get_user_info(user_id)
                await client.send_message(user, message)
    f = open(reminders_file, 'w')
    json.dump(reminders, f, indent=4)
    f.close()

    asyncio.ensure_future(reminder_event())


def init_subs():
    if not os.path.isfile(subscribers_file):
        try:
            subs = {el: [] for el in events}
            with open(subscribers_file, 'w') as f:
                json.dump(subs, f)
        except:
            return False
    return True


def get_subs():
    subs = {el: [] for el in events}
    if init_subs():
        try:
            with open(subscribers_file, 'r') as f:
                subs = json.load(f)
        except:
            pass
    return subs


def set_subs(subs):
    if init_subs():
        try:
            with open(subscribers_file, 'w') as f:
                json.dump(subs, f)
        except:
            return False
    else:
        return False
    return True


def subscribe(event, user_id):
    subs = get_subs()
    try:
        if user_id not in subs[event]:
            subs[event].append(user_id)
            return set_subs(subs)
        else:
            return False
    except KeyError:
        if event in events:
            subs[event] = []
            if set_subs(subs):
                return subscribe(event, user_id)
            else:
                return False
    except:
        return False


def unsubscribe(event, user_id):
    subs = get_subs()
    try:
        if user_id in subs[event]:
            subs[event].remove(user_id)
            return set_subs(subs)
        else:
            return False
    except KeyError:
        if event in events:
            subs[event] = []
            if set_subs(subs):
                return unsubscribe(event, user_id)
            else:
                return False
    except:
        return False


async def tag_subscribers(channel, event, show_help=True):
    subs = get_subs()
    tag_msg = ''
    try:
        for user_id in subs[event]:
            tag_msg += '<@%s>' % user_id
    except KeyError:
        pass
    if show_help:
        tag_msg += "\n\n For more info on event notifications type **!help** or **!commands**"
    await client.send_message(channel, tag_msg)


async def test_event():
    await asyncio.sleep(10)

    channel = client.get_channel(notify_channel_id)
    if channel is None:
        channel = next(iter(client.servers))
    em = discord.Embed(description='IT\'S **HABBENING**!', colour=0xffffff)
    em.set_author(name='Test', icon_url=client.user.avatar_url)
    await client.send_message(channel, embed=em)
    await tag_subscribers(channel, 'test')

    asyncio.ensure_future(test_event())


def is_legit_ns(message, n):
    match = re.search(r'\n(# )?(\[)?.+? rolls (\d+) \((\d+)-(\d+)\).', message)
    if match:
        roll = int(match.group(1))
        lower = int(match.group(2))
        upper = int(match.group(3))
        div = 1
        scale = 10 ** n
        for i in range(1, n):
            div = div * 10 + 1
        return upper - lower >= (scale - 1) and (roll % scale) % div == 0
    else:
        return False


def is_legit_dubs(message):
    return is_legit_ns(message, 2)


def get_remind_arg_type(arg):
    type = ReminderArgType.unknown  # Unknown
    if re.match(r'^(([01]?\d)|(2[0-3])+):([0-5]\d)$', arg):
        type = ReminderArgType.std_time  # Standard time
    elif re.match(r'^\d+$', arg):
        type = ReminderArgType.integer  # Integer
    elif re.match(r'^(sunday|monday|tuesday|wednesday|thursday|friday|saturday)$', arg, re.IGNORECASE):
        type = ReminderArgType.weekday  # Weekday
    elif re.match(r'^h', arg, re.IGNORECASE):
        type = ReminderArgType.hour_word  # Hour word
    elif re.match(r'^m', arg, re.IGNORECASE):
        type = ReminderArgType.minute_word  # Minute word
    elif re.match(r'^d', arg, re.IGNORECASE):
        type = ReminderArgType.day_word  # Day word
    elif re.match(r'^every$', arg, re.IGNORECASE):
        type = ReminderArgType.recurring  # Recurring enabled
    return type


def day_code(day):
    for i in range(0, len(weekdays)):
        if weekdays[i] == day.lower():
            return i


def seconds_to_str(seconds):
    str = ''
    seconds += 1
    if seconds > 24 * 60 * 60:
        days = int(seconds / (24 * 60 * 60))
        str += '%d days ' % days
        seconds -= days * 24*60*60
    if seconds > 60 * 60:
        hours = int(seconds / (60 * 60))
        str += '%d hours ' % hours
        seconds -= hours * 60 * 60
    if seconds > 60:
        minutes = int(seconds / 60)
        str += '%d minutes ' % minutes
        seconds -= minutes * 60
    if len(str) < 1:
        str = '0 min'
    return str

client.run(prod_token)
